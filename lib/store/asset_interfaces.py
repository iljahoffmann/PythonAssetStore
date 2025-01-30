from abc import ABC, abstractmethod
from lib.persistence import IPersistentObject
from lib.store.update_context import UpdateContext


class IAction(IPersistentObject, ABC):

	@abstractmethod
	def update_required(self, asset, context):
		"""
		Determines if an update is required.
		:param asset: Asset
		:param context: UpdateContext
		:return: bool
		"""
		pass

	@abstractmethod
	def pre_update(self, asset, context, args: dict):
		"""
		Called immediately before dependencies are updated.
		Default is to do nothing.
		:param asset: Asset
		:param args: dict
		:param context: UpdateContext
		"""
		pass

	@abstractmethod
	def pre_execute(self, asset, context, **kwargs):
		"""
		Called immediately before execute.
		Default is to do nothing.
		:param asset: Asset
		:param context: UpdateContext
		"""
		pass

	@abstractmethod
	def execute(self, asset, context, **kwargs):
		"""
		Executes the action.
		:param asset: Asset
		:param context: UpdateContext
		:return: object
		"""
		pass

	@abstractmethod
	def post_execute(self, asset, context, call_result, **kwargs):
		"""
		Called immediately after execute.
		Default is to do nothing.
		:param asset: Asset
		:param context: UpdateContext
		:param call_result: object - the result of calling the action's execute method
		"""
		pass

	@abstractmethod
	def update_required(self, asset, context, **kwargs):
		"""
		Called to determine if the action needs to be called.
		Default uses asset.action_args['update_strategy'], which defaults to 'std': True
		:param asset: Asset
		:param context: UpdateContext
		:return: bool
		"""
		pass

	@abstractmethod
	def update_dependency(self, asset, dependency_reference, args: dict, context, **kwargs):
		"""
		Redefines how dependencies are updated (especially in template update).
		:param asset: Asset
		:param dependency_reference: IAssetReference
		:param args: dict
		:param context: UpdateContext
		:return: Asset
		"""
		pass

	@abstractmethod
	def get_help(self):
		"""
		Provides help or guidance for the action.
		:return: dict
		"""
		pass

	@abstractmethod
	def accepts_inner_access(self):
		"""
		Determines if the action is __inner_* protocol aware.
		Default is not aware.
		:return: bool
		"""
		pass


class IAssetReference(IPersistentObject, ABC):
	"""
	Interface representing a reference to an asset. Derived classes must implement methods
	to retrieve the referenced asset and provide string representations.
	"""

	def get_asset(self, context: "UpdateContext") -> "Asset":
		"""Retrieve the referenced asset."""
		raise NotImplementedError()

	def get_name(self):
		"""Return the name of the asset reference if available."""
		raise NotImplementedError()

	def __str__(self):
		"""String representation of the asset reference."""
		raise NotImplementedError()


class IUpdateStrategy(ABC):
	@classmethod
	@abstractmethod
	def update(cls, asset, context, **kwargs):
		pass


class IPermissionProvider(ABC):
	@abstractmethod
	def get_permissions(self) -> "UnixPermissions":
		pass

	@abstractmethod
	def set_permissions(self, permissions: "UnixPermissions"):
		pass

