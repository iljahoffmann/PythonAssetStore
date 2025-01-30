from typing import MutableMapping, Sequence

from lib.call_result import ErrorResult, ValidResult
from lib.store.asset_interfaces import IUpdateStrategy, IAssetReference, IAction
from lib.store.update_context import UpdateContext


def get_action_and_args(asset) -> (IAction, MutableMapping):
	action = asset.action

	args_from_asset = []
	while isinstance(action, IAssetReference):
		referred_asset = action.get_asset()
		args_from_asset.append(referred_asset.action_args)
		action = referred_asset.action
	args_from_asset.append(asset.action_args)

	if not isinstance(action, IAction):
		raise ValueError(f'referred action is of invalid type {action.__class__}"')

	action_args = {}
	while len(args_from_asset) > 0:
		args = args_from_asset.pop()
		action_args.update(args)

	return action, action_args


def execute_action(asset: "Asset", action: IAction, action_args: MutableMapping[str, object], context: UpdateContext):
	try:
		action.pre_execute(asset, context, **action_args)
	except Exception as pre_exception:
		return asset.set_result(ErrorResult.from_exception(pre_exception, message='in pre_execute()'))

	try:
		result = action.execute(asset, context, **action_args)
	except Exception as exception:
		return asset.set_result(ErrorResult.from_exception(exception, message='action failed'))

	try:
		if post_result := action.post_execute(asset, context, result, **action_args):
			result = post_result
	except Exception as exception:
		return asset.set_result(ErrorResult.from_exception(exception, message='in post_execute()'))

	return asset.set_result(result if isinstance(result, ErrorResult) else ValidResult(result))


def _update_without_user_params(asset: "Asset", context: UpdateContext, action: IAction, action_args):
	# since the action-result is a member of the asset, updating without parameters is functionally
	# equivalent to the 'read' operation on the asset: it is assumed that the asset was set up with
	# secure parameters and the user accesses the configured value/result only.
	if context.permission_granted(asset.get_permissions(), 'r'):
		if context.permission_granted(asset.get_permissions(), 'w'):
			return execute_action(asset, action, action_args, context)
		else:
			return execute_action(asset.clone(), action, action_args, context)
	raise PermissionError('read permission denied')

def _parametrized_update(asset: "Asset", context, action: IAction, action_args, **kwargs):
	# 'true' Update requires 'execute' permission.
	if context.permission_granted(asset.get_permissions(), 'x'):
		action_args.update(kwargs)
		return execute_action(asset.clone(), action, action_args, context)
	raise PermissionError('execute permission denied')


class UpdateStrategyBasic(IUpdateStrategy):
	"""
	The basic update strategy is to call the action unconditionally and not threaded.
	"""
	@classmethod
	def update(cls, asset, context, **kwargs):
		action, action_args = get_action_and_args(asset)

		if len(kwargs) == 0:
			return _update_without_user_params(asset, context, action, action_args)
		else:
			return _parametrized_update(asset, context, action, action_args, **kwargs)


class UpdateStrategyMake(IUpdateStrategy):
	@classmethod
	def update(cls, asset, context, **kwargs):
		def _update_required():
			update_required = cls.update_required(asset, context)
			if not update_required:
				for d in dependency_assets:
					if cls.update_required(d, context):
						update_required = True
			return update_required

		action = asset.action
		action.pre_update()

		dependencies: Sequence[IAssetReference] = asset.dependencies;
		dependency_assets = [d.get_asset() for d in dependencies]

		if not _update_required():
			return asset

		updated_dependencies = []
		for dependency in dependency_assets:
			updated_dependency = action.update_dependency(asset, context, dependency, **kwargs)
			updated_dependencies.append(updated_dependency)
		pass

	@classmethod
	def update_required(cls, asset, context):
		last_build = asset.get_last_build_date()
		build_required = (
				asset.is_phony() or
				(asset.get_result() is None) or
				(last_build is not None and last_build < asset.get_last_modification_date())
		)
		return build_required


update_strategies = {
	"basic": UpdateStrategyBasic,
	"make": UpdateStrategyMake,
	"std": UpdateStrategyBasic
}
