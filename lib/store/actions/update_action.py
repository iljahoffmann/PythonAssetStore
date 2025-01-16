from typing import MutableMapping

from lib.module_loader import get_source_info, load_or_update_module
from lib.call_result import ErrorResult
from lib.json_schema import Object, Optional, Type
from lib.dispatcher_decorator import DispatchedNamespace
from lib.value_predicate import is_of_type, optional

from lib.store.action import IAction, StatelessDispatchedAction
from lib.store.asset import Asset


asset_description_schema = Object({
	'action': Object({
		'module_path': Type(str),
		'class_name': Type(str),
		'args': Optional(Object(keys=Type(str)))
	}),
	'action_args': Optional(Object(keys=Type(str))),
	'mode': Type(int, str)
})


def make_asset_description(
	action_module_path: str,
	action_class_name: str,
	mode: str|int,
	action_args: MutableMapping[str, object]|None = None,
	asset_action_args: MutableMapping[str, object]|None = None
):
	result = {
		'action': {
			'module_path': action_module_path,
			'class_name': action_class_name,
		},
		'mode': mode
	}

	if action_args:
		result['action']['args'] = action_args

	if asset_action_args:
		result['action_args'] = asset_action_args

	trace = []
	if not asset_description_schema.validate(result, trace=trace):
		raise ValueError(str(trace))

	return result


update_asset_action_namespace = DispatchedNamespace()


class UpdateAssetAction(StatelessDispatchedAction):
	@staticmethod
	def _get_action_instance(file, class_name, ctor_parameters, namespace:MutableMapping[str, "module"]=None):
		action_module = load_or_update_module(file, namespace=namespace)
		updated_class = getattr(action_module, class_name)
		action_from_module: IAction = updated_class(**ctor_parameters)
		print('mod', id(action_module), '/', 'cls', id(action_from_module))
		return action_module, action_from_module

	@update_asset_action_namespace.conditional(
		asset_description=asset_description_schema.validate
	)
	def _execute(self,
	        asset,
	        context,
	        path_to_asset:str,
	        asset_description,
	        namespace=None
	):
		action_description = asset_description['action']
		action_module, action_from_module = self._get_action_instance(
			action_description['module_path'],
			action_description['class_name'],
			action_description.get('args', {}),
			namespace=namespace
		)

		created_asset = Asset(
			action_from_module,
			asset_description.get('action_args', {})
		)
		context.store.store(context, created_asset, path=path_to_asset, mode=asset_description['mode'])
		return f'stored {action_module}:{action_description["class_name"]} in {path_to_asset}'
		pass

	@update_asset_action_namespace.conditional()
	def _execute(self, asset, context, path_to_asset:str, namespace=None):
		update_asset = context.store.acquire(context, path_to_asset)
		action: IAction = update_asset.action
		ctor_parameters = action.ctor_parameter()
		file, class_name = get_source_info(action)
		try:
			action_module, action_from_module = self._get_action_instance(
				file,
				class_name,
				ctor_parameters,
				namespace=namespace
			)
		except Exception as ex:
			return ErrorResult.from_exception(ex)

		update_asset.action = action_from_module
		return f'reloaded {action_module}:{class_name} in {path_to_asset}'

	# Fallthrough
	@update_asset_action_namespace.conditional()
	def _execute(self, asset, context, **kwargs):
		raise ValueError(f'no matching handler found')

	def get_help(self):
		pass


if __name__ == '__main__':
	def main():
		request = make_asset_description(
			'[]/lib/store/actions/read_dir.py',
			'ReadDir',
			'775'
		)

		updater =  UpdateAssetAction()
		updater.execute(None, None, path_to_asset='test.test2', asset_description=request)

		pass

	main()
