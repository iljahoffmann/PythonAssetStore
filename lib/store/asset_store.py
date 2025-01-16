import os
import traceback
from collections.abc import MutableMapping
from abc import ABC, abstractmethod
from struct import unpack
from xml.etree.ElementTree import indent

# from lib.ABC import AbstractBaseClassCalled
from lib.persistence import BasicPersistentObject, to_json, from_json
from lib.path_op import TreePath, path_iter, path_set, path_del
from lib.default import default_or_raise
from lib.project_path import ProjectPath
from lib.shared_dict import SharedDict
from lib.store.asset_interfaces import IPermissionProvider
from lib.store.user_registry import UserRegistry
from lib.store.unix_permissions import UnixPermissions
from lib.store.actions.read_dir import ReadDir
from lib.store.asset import Asset
from lib.store.update_context import UpdateContext


# The AssetStore uses basic concepts of a POSIX file system to represent a system of nested
# dictionaries with values of another type than mappings as nodes, that ultimately resolve into 'Assets'
# (see lib.store.asset).

# The assets are stored as persistent JSON encoded texts using a given storage strategy.
#
# An integer node represents an ID, that the storage strategy can use to retrieve or store the actual serialized asset.
#
# Symbolic links are held as SymLink instances. When following a symbolic link, the associated path is traversed using
# all involved permissions and credentials. All objects in the store are referred to in the same way when
# using symbolic links.
#
# Hard links are either held as HardLink-instances when referring directories or IAssetSources, or as an inode ID when
# established on an asset. A detection mechanism prevents the user from forming loops when creating hard
# links on directories, however, when links of any kind are used, the strict tree invariant (exactly one path from
# the root to any entry) is never truly fulfilled.
#
# IAssetSource is the interface that classes implement, that themselves are not assets but are able to produce or
# retrieve assets.
#
# An asset source may implement the 'inner access' protocol (see **), which allows it to represent a store-compatible
# tree of assets.

class IAssetStorage(ABC):
	@abstractmethod
	def save(self, asset: Asset, context: UpdateContext):
		pass

	@abstractmethod
	def load(self, asset_id: int, context: UpdateContext) -> Asset:
		pass

	@abstractmethod
	def delete(self, asset: Asset, context: UpdateContext) -> Asset:
		pass

	@abstractmethod
	def load_asset_tree(self) -> MutableMapping[str, object]:
		pass

	@abstractmethod
	def save_asset_tree(self, asset_tree: MutableMapping[str, object]) -> bool:
		pass

	@abstractmethod
	def load_asset_id(self) -> int:
		pass

	@abstractmethod
	def save_asset_id(self, asset_id) -> bool:
		pass


class IAssetSource(IPermissionProvider, ABC):
	@abstractmethod
	def get_asset(self) -> Asset:
		pass


class IAssetReference(IAssetSource, ABC):
	pass


class IStoreLink(IPermissionProvider, ABC):
	@abstractmethod
	def as_path(self):
		pass


class SymLink(BasicPersistentObject, IStoreLink):
	def __init__(self, path, permissions=None):
		self.path = path
		self.permissions = permissions

	def ctor_parameter(self):
		return {'path': self.path, 'permissions': self.permissions}

	def get_permissions(self) -> UnixPermissions | None:
		return self.permissions

	def set_permissions(self, permissions: UnixPermissions | None):
		self.permissions = permissions

	def as_path(self):
		return self.path


class HardLink(SharedDict, BasicPersistentObject, IStoreLink):
	def __init__(self, path, shared_dict, *args, **kwargs):
		super().__init__(shared_dict, *args, **kwargs)
		self.path = path

	def ctor_parameter(self):
		return {'path': self.path}

	def as_path(self):
		return self.path

	def get_permissions(self) -> UnixPermissions | None:
		return self.get('')

	def set_permissions(self, permissions: UnixPermissions | None):
		self[''] = permissions


class AssetFileStorage(IAssetStorage):
	tree_filename = 'directory'
	id_filename = 'nextId'

	def __init__(self, base_directory):
		self.base_directory = ProjectPath.local(base_directory)
		if not os.path.exists(self.base_directory):
			os.mkdir(self.base_directory)

	def _filename(self, name):
		return os.path.join(self.base_directory, f'{str(name)}.json')

	def _load_object(self, filename):
		with open(self._filename(filename), "r") as f:
			packed = f.read()
			unpacked = from_json(packed)
			return unpacked

	def _save_object(self, filename, obj):
		packed = to_json(obj, indent=2)
		with open(self._filename(filename), "w") as f:
			f.write(packed)

	def load(self, asset_id: int, context: UpdateContext) -> Asset:
		return self._load_object(asset_id)

	def save(self, asset: Asset, context: UpdateContext):
		asset_id = asset.get_id()
		self._save_object(asset_id, asset)

	def delete(self, asset: Asset, context: UpdateContext) -> Asset:
		pass

	def load_asset_tree(self) -> MutableMapping[str, object]:
		try:
			return self._load_object(AssetFileStorage.tree_filename)
		except Exception as ex:
			print(str(ex))
			return AssetStore.empty_root()

	def save_asset_tree(self, asset_tree: MutableMapping[str, object]):
		self._save_object(AssetFileStorage.tree_filename, asset_tree)

	def load_asset_id(self) -> int:
		try:
			return self._load_object(AssetFileStorage.id_filename)
		except Exception as ex:
			print(str(ex))
			return AssetStore.first_id()

	def save_asset_id(self, asset_id):
		self._save_object(AssetFileStorage.id_filename, asset_id)


class AssetStore:
	runtime_key = 'runtime'
	deleted_directory_base = 'deleted'
	allow_access_by_default = True
	default_root_permissions =  UnixPermissions('root', 'system', 0o775)

	def __init__(
			self,
			storage: IAssetStorage
	):
		self.storage = storage
		self.asset_tree = AssetStore.empty_root()
		self.asset_by_id_cache = {}
		self.next_asset_id = AssetStore.first_id()

	@staticmethod
	def empty_root():
		default_root = {'': AssetStore.default_root_permissions}
		return default_root

	@staticmethod
	def first_id():
		return 100_000

	@staticmethod
	def _may_enter_directory(context: UpdateContext, permissions) -> bool:
		# As in POSIX, the only permission required to traverse through directories given known names is "x"
		if permissions:
			return context.permission_granted(permissions, 'x')
			# return permissions.is_right_granted(context.get_user_registry(), context.get_effective_user(), 'x')
		else:
			return AssetStore.allow_access_by_default

	@staticmethod
	def _may_read_directory(context: UpdateContext, permissions) -> bool:
		# Reading the existing keys from a directory requires "r" permission
		if permissions:
			return context.permission_granted(permissions, 'r')
			# return permissions.is_right_granted(context.get_user_registry(), context.get_effective_user(), 'r')
		else:
			return AssetStore.allow_access_by_default

	@staticmethod
	def _may_write_directory(context: UpdateContext, permissions, node, key) -> bool:
		# creating or removing assets require write permissions on directories; on shared directories,
		# an existing entry can only be changed by its owner.
		if permissions:
			if not context.permission_granted(permissions, 'w'):
				return False

			if key in node and permissions.is_right_granted(context.get_user_registry(), '*', 't'):
				existing_entry = node[key]
				entry_permissions = None
				if isinstance(existing_entry, MutableMapping):
					entry_permissions = existing_entry.get('', permissions)
				elif isinstance(existing_entry, IPermissionProvider):
					entry_permissions = existing_entry.get_permissions()
				else:
					raise ValueError(f'invalid directory entry: {existing_entry}')
				# entry exists, so check shared-permission: may write if owner
				return context.get_user() == entry_permissions.user_name

			else:
				# new key - write permission is sufficient
				return True
			# return permissions.is_right_granted(context.get_user_registry(), context.get_effective_user(), 'w')
		else:
			return AssetStore.allow_access_by_default

	@staticmethod
	def _make_permissions(context: UpdateContext, mode):
		permissions = UnixPermissions.make_permission(
			context.get_user_registry(),
			context.get_user(),
			context.get_group(),
			mode=mode
		)
		return permissions

	def _set_directory_permissions(self, context: UpdateContext, directory, mode):
		permissions = self._make_permissions(context, mode)
		directory[''] = permissions

	def _get_next_id(self):
		result = self.next_asset_id
		self.next_asset_id += 1
		return result

	def _acquire_by_id(self, context: UpdateContext, asset_id: int, default):
		try:
			if asset_id in self.asset_by_id_cache:
				return self.asset_by_id_cache[asset_id]
			asset = self.storage.load(asset_id, context)
			self.asset_by_id_cache[asset_id] = asset
			return asset
		except Exception as ex:
			return default_or_raise(default, str(ex))

	def _int_acquired(self, current, tree_path, current_path, default):
		is_last_component = len(tree_path.components) == len(current_path)
		if is_last_component:
			return self._acquire_by_id()
		else:
			raise Exception('not yet implemented')

	def _symlink_acquired(self, current, tree_path, current_path, default):
		asset = self._acquire_by_id(current)
		is_last_component = len(tree_path.components) == len(current_path)

	def _link_acquired(self, current, tree_path, current_path, default):
		pass

	def _asset_source_acquired(self, current, tree_path, current_path, default):
		pass

	def _node_acquired(self, current, tree_path, current_path, default):
		# int as a value is the inode number
		if isinstance(current, int):
			return self._int_acquired(current, tree_path, current_path, default)
		# string (treepath) as a value is a symlink
		if isinstance(current, str):
			return self._symlink_acquired(current, tree_path, current_path, default)
		elif isinstance(current, IAssetSource):
			return self._asset_source_acquired(current, tree_path, current_path, default)

		return default_or_raise(default, f'invalid directory entry at {current_path}')

	@staticmethod
	def _get_node_permissions(node) -> UnixPermissions|None:
		if isinstance(node, MutableMapping):
			return node.get('')
		elif isinstance(node, IPermissionProvider):
			return node.get_permissions()
		else:
			return None

	def _get_node(self, context: UpdateContext, path: TreePath) -> (object, [str], MutableMapping[str, bool], str):
		# returns:
		# node, current_path, node_permissions, error

		def _effective_permissions():
			return current_permissions if current_permissions else last_directory_permissions

		if path.is_empty():
			return self.asset_tree, [], self.asset_tree.get(''), None

		current = self.asset_tree
		current_path = []
		current_permissions = current['']   # root directory is guaranteed to have a permission entry
		last_directory_permissions = current_permissions

		for component in path.components:
			current_path.append(component)

			if not isinstance(current, MutableMapping):
				return current, current_path, _effective_permissions(), None

			if not self._may_enter_directory(context, _effective_permissions()):
				return current, current_path, _effective_permissions(), f'permission to enter {current_path} is denied'

			entry = current.get(component)
			if entry is None:
				return current, current_path, _effective_permissions(), f'path not found: {current_path}'

			current = entry
			current_permissions = self._get_node_permissions(current)
			if current_permissions:
				last_directory_permissions = current_permissions

		return current, current_path, _effective_permissions(), None

	@staticmethod
	def _directory_to_json(node, permissions):
		contents = [f for f in node if f != '']
		result = {
			'permissions': permissions,
			'contents': contents
		}
		return result

	@staticmethod
	def _valid_store_path(path:str):
		return not '[' in path

	def read_directory(self, context: UpdateContext, path: TreePath | str) -> MutableMapping[str, object]:
		tree_path = TreePath(path)
		# do not accept array indices in path
		if not AssetStore._valid_store_path(str(tree_path)):
			raise ValueError(f'invalid path: "{path}"')

		node, node_path, node_permissions, error = self._get_node(context, path)
		if error or not isinstance(node, MutableMapping):
			raise ValueError(f"{path} is not a directory")

		if not self._may_read_directory(context, node_permissions):
			raise PermissionError('read access denied')

		return AssetStore._directory_to_json(node, node_permissions)

	def _acquire_by_path(self, context: UpdateContext, path: TreePath | str, default):
		tree_path = TreePath(path)
		# do not accept array indices in path
		if not AssetStore._valid_store_path(str(tree_path)):
			return default_or_raise(default, f'invalid path: "{path}"')

		node, node_path, _, error = self._get_node(context, tree_path)
		if error:
			return default_or_raise(default, error)

		if isinstance(node, MutableMapping):
			# got a directory here - return an asset for access
			return Asset(ReadDir(), path=str(path))
		elif isinstance(node, int):
			return self._acquire_by_id(context, asset_id=node, default=default)
		else:
			pass

	def acquire(self, context: UpdateContext, path=None, asset_id=None, default=None) -> Asset:
		if path and asset_id:
			raise ValueError('acquire() called with path and asset id - only one of them is allowed')

		if path:
			return self._acquire_by_path(context, path, default=default)
		elif asset_id:
			return self._acquire_by_id(context, asset_id=asset_id, default=default)
		else:
			raise ValueError('acquire() called without path or asset id')

	def _set_node(self, context: UpdateContext, path: TreePath, value, mode=None):
		def _effective_permissions():
			nonlocal current_permissions, last_permissions
			return current_permissions if current_permissions else last_permissions

		def _perform_write_on_node():
			pass

		def _perform_write():
			if node_is_directory:
				entry_key = tree_path.components[-1]
				if self._may_write_directory(context, _effective_permissions(), node, entry_key):
					node[entry_key] = value
					# self._set_directory_permissions(context, node, mode)
				else:
					raise PermissionError(f'no write permission for {str(container_path)}')
			else:
				_perform_write_on_node()

		def _handover_write_to_node():
			pass

		def _perform_enter():
			nonlocal current_permissions, last_permissions

			current_permissions = node.get('') if node_is_directory else _permissions_for_entry()
			if node_is_directory:
				if not self._may_enter_directory(context, _effective_permissions()):
					raise PermissionError(f'not allowed to enter {str(container_path)}')
			else:
				_handover_write_to_node()

			if current_permissions:
				last_permissions = current_permissions

		def _permissions_for_entry():
			if isinstance(node, IPermissionProvider):
				return node.get_permissions()
			else:
				return None

		def _missing_directory(tree_iterator):
			key = tree_iterator.components[tree_iterator.index]
			if not self._may_write_directory(context, _effective_permissions(), tree_iterator.current, tree_iterator.index):
				raise PermissionError(f'permission to create "{key}" denied')

			new_directory = {}
			tree_iterator.current[key] = new_directory
			return new_directory

		tree_path = TreePath(path)      # path is not None, but may be empty
		path_len = len(tree_path.components)
		if path_len == 0:
			raise PermissionError('root can not be assigned')

		# locate containing node - last component is to be the name there
		container_path = TreePath(tree_path.components[:-1])
		node = self.asset_tree
		current_permissions = self.asset_tree['']  # root directory is guaranteed to have a permission entry
		last_permissions = current_permissions
		node_is_directory = True

		for node in path_iter(self.asset_tree, container_path, on_miss=_missing_directory):
			node_is_directory = isinstance(node, MutableMapping)
			_perform_enter()  # modifies current- and last-perms / might hit a node that can not be entered (directly)

		# reached the destination, now set
		try:
			_perform_write()
		except Exception as ex:
			print(str(ex))
			traceback.print_exc()
			raise
		pass

	@staticmethod
	def _permissions_from_mode(context: UpdateContext, mode):
		if not mode:
			return None

		return UnixPermissions.make_permission(
			context.get_user_registry(),
			user_name=context.get_user(),
			group_name=context.get_group(),
			mode=mode
		)

	def store(self, context: UpdateContext, asset: Asset, path=None, accept_inner_access=False, mode=None):
		# ensure asset has an ID and save to storage
		if asset.get_id() == -1:
			asset.set_id(self._get_next_id())

		if mode:
			asset_permissions = self._permissions_from_mode(context, mode)
			asset.set_permissions(asset_permissions)

		self.storage.save(asset, context)

		# with no path, the asset was just saved -- with path, insert it into the tree:
		if path:
			self._set_node(context, path, asset.get_id(), mode=mode)
			self.asset_by_id_cache[asset.get_id()] = asset

		pass

	def remove(self, context: UpdateContext, path:str|TreePath):
		tree_path = TreePath(path)
		if len(tree_path) == 0:
			raise ValueError('root directory can not be removed')

		container_path = tree_path[:-1]
		container, current_path, container_permissions, error = self._get_node(context, container_path)
		if error:
			raise PermissionError(error)

		raise Exception('work in progress')


	def mkdir(self, context: UpdateContext, path, mode=None):
		tree_path = TreePath(path)
		if tree_path.is_empty():
			raise ValueError('path is not valid')

		new_directory = {}
		if mode:
			new_directory[''] = self._permissions_from_mode(context, mode)

		self._set_node(context, path, new_directory)

	def load(self):
		self.asset_tree = self.storage.load_asset_tree()
		self.next_asset_id = self.storage.load_asset_id()

	def save(self):
		self.storage.save_asset_tree(self.asset_tree)
		self.storage.save_asset_id(self.next_asset_id)

	@staticmethod
	def query(context: UpdateContext, path: str, **kwargs):
		asset = context.store.acquire(context, path=path)
		result = asset.update(context, **kwargs)
		return  result


if __name__ == '__main__':
	from lib.store.actions.action_tests import TestDispatchedAction, TestAction
	from lib.store.actions.update_action import UpdateAssetAction, make_asset_description

	def _make_user_registry():
		user_registry = UserRegistry()
		user_registry.make_entity("root")
		user_registry.make_entity("alice")
		user_registry.make_entity("bob")
		user_registry.make_entity("charly")

		user_registry.make_entity("system")
		user_registry.make_entity("team")
		user_registry.make_entity("developers")

		# all team members are devs
		user_registry.add_layer_to_entity("root", "system")
		user_registry.add_layer_to_entity("team", "developers")

		# bob is a member of the team
		user_registry.add_layer_to_entity("bob", "team")
		return user_registry

	def main():
		user_registry = _make_user_registry()
		store = AssetStore(storage=AssetFileStorage('[]/store'))
		store.load()

		context = UpdateContext(
			store=store,
			user_registry=user_registry,
			user='root',
			group='system'
		)

		read_dir_asset = Asset(ReadDir())
		test_asset = Asset(
			TestDispatchedAction(), permissions=UnixPermissions('root', 'system', mode='775')
			# TestAction(), permissions=UnixPermissions('root', 'system', mode='775')
		)
		store.store(context, test_asset, 'test.test')

		store.remove(context, 'test.test')

		update_asset = Asset(
			UpdateAssetAction(), permissions=UnixPermissions('root', 'system', mode='770')
		)

		request = make_asset_description(
			'[]/lib/store/actions/action_tests.py',
			'TestAction',
			'775'
		)

		update_result = update_asset.update(context, path_to_asset='test.test2', asset_description=request)
		test2_acquired = store.acquire(context, path='test.test2')
		test2_result = test2_acquired.update(context)

		update_asset.update(context, path_to_asset='test.test3', asset_description=request)
		test3_acquired = store.acquire(context, path='test.test3')
		test3_result = test3_acquired.update(context)

		try:
			test_result1 = test_asset.update(context, count=17.4, option='-o', bogus=True)
			print("1:", test_result1.get_result())

			reloaded_test = update_asset.update(context, path_to_asset='test.test')

			test_asset2 = store.acquire(context, path='test.test')
			test_result2 = test_asset2.update(context, count=17.4, option='-o', bogus=True)
			print("2:", test_result2.get_result())

			test_result1 = test_asset.update(context, count=17.4, option='-o', bogus=True)
			print("1:", test_result1.get_result())

			store.mkdir(context, 'tmp', mode='1775')
			ls = store.acquire(context, path='bin.ls', default=KeyError())
			updated_ls = ls.update(context, path='test', html=1)
			print("ls:", updated_ls.get_result())
			pass
		except Exception as ex:
			print(str(ex))

		store.store(context, read_dir_asset, path='bin.ls', mode=0o754)

		store.save()
		pass

	main()
