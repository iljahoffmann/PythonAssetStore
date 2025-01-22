from lib.store.asset import Asset
from lib.store.update_context import UpdateContext


class ActionRegistry:
	"""
	A registry to maintain the names of decorated classes and their associated metadata.
	"""
	_registry = {}

	@classmethod
	def _register_class(cls, class_obj, **kwargs):
		"""
		Registers the name of a class in the registry along with optional metadata.
		The key for storage includes the module name and class name.
		"""
		cls_name = f"{class_obj.__module__}.{class_obj.__name__}"
		kwargs['class'] = class_obj
		cls._registry[cls_name] = kwargs
		print(f"Registered class: {cls_name} with metadata: {kwargs}")

	@classmethod
	def get_registered_classes(cls):
		"""
		Returns the dictionary of registered class names and their metadata.
		"""
		return cls._registry

	# <<Decorator>>
	@classmethod
	def store_asset(cls, path:str, user:str='root', group:str='system', mode='775',  **kwargs):
		"""
		A class method that acts as a decorator to register classes with metadata.
		"""
		def wrapper(class_obj):
			cls._register_class(class_obj, **full_args)
			return class_obj

		full_args = {'path': path, 'user': user, 'group': group, 'mode': mode, **kwargs}
		return wrapper

	@classmethod
	def create_registered_actions(cls, context):
		for entry in cls._registry.values():
			the_class = entry['class']
			asset_args = entry.get('asset_args', {})
			action_args = entry.get('action_args', {})
			the_asset = Asset(the_class(**action_args), **asset_args)
			asset_context = context.copy()
			for arg in ['user', 'group']:
				asset_context[arg] = entry[arg]
			asset_context['identity'] = [(entry['user'], entry['group'])]
			context.store.store(asset_context, the_asset, path=entry['path'], mode=entry['mode'])

		pass
