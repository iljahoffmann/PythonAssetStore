from threading import RLock

from lib.store.unix_permissions import UnixPermissions


class UpdateContext(dict):
	"""
	Required settings to perform an operation on the store or its assets.
	Args:
		store (AssetStore): required - the asset store to operate on.
		user_registry (UserRegistry): required - the registry used to validate user access.
		user (str): required - the name of the current user.
		group (str): required - the name of the current group.
	"""
	def __init__(self, seq=None, **kwargs):
		super().__init__(seq if seq else [], **kwargs)
		self.lock = RLock()
		if not 'store' in kwargs:
			raise KeyError('"store" not set but is required')

		if not 'user_registry' in kwargs:
			raise KeyError('"user_registry" not set but is required')

		self['identity'] = [(self['user'], self['group'])]

	def __getattr__(self, item):
		try:
			# Attempt to find the attribute as a key in the dictionary
			return self[item]
		except KeyError:
			# Raise AttributeError if the key is not found
			raise AttributeError(f"'{type(self).__name__}' object has no attribute '{item}'")

	def copy(self):
		return UpdateContext(**self)

	def push_identity(self, user, group):
		self.get('identity').append((user, group))

	def pop_identity(self):
		idents = self.get('identity')
		if len(idents) > 1:
			return idents.pop()
		else:
			raise Exception("base identity can not be removed")

	def get_user(self):
		# first entry of the last tuple
		return self.get('identity')[-1][0]

	def get_real_user(self):
		return self['user']
		# same value as:
		# first entry of the first tuple
		# return self.get('identity')[0][0]

	def get_group(self):
		return self.get('identity')[-1][1]

	def get_real_group(self):
		return self['group']
		# same value as:
		# return self.get('identity')[0][1]

	def get_user_registry(self):
		return self.get('user_registry')

	def permission_granted(self, node_permissions: "UnixPermissions", requested_right: str):
		return node_permissions.is_right_granted(self.get_user_registry(), self.get_user(), requested_right)

	def make_permission(self, mode):
		result = UnixPermissions(self.get_user(), self.get_group(), mode=mode)
		return result
