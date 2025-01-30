from abc import ABC, abstractmethod
from lib.persistence import BasicPersistentObject
from lib.call_result import ErrorResult
from lib.store.asset_interfaces import IAction
from lib.store.update_strategy import update_strategies
from lib.store.help import Help


class BasicAction(BasicPersistentObject, IAction, ABC):
	def update_dependency(self, asset, context, dependency, **kwargs):
		updated_dependency = dependency.update({}, context)  # Default: no parameters for template update
		return updated_dependency

	def update_required(self, asset, context):
		strategy = asset.action_args.get('update_strategy', 'std')
		return update_strategies[strategy].default_update_required(asset, context)

	def pre_update(self, asset, args: dict, context):
		pass

	def pre_execute(self, asset, context, **kwargs):
		pass

	def post_execute(self, asset, context, call_result, **kwargs):
		pass

	def accepts_inner_access(self):
		"""
		Whether the inner access protocol is supported: if so, additional path components the client provided when
		acquiring, that were not used to locate the asset, are accepted and provided to the asset's execute() kwargs.

		For example, if the client addressed 'app.store.items.1' and the asset is bound to app.store.items, the
		additional component '1' is assumed a parameter to the assets action.

		Three different names for get-, set- or delete-operations are used for the additional components list:
		'_inner_get': used with a get request,
		'_inner_set' + 'inner_value': for a set request, and
		'_inner_del': when a delete-operation is requests.

		The action has to check the mode by testing the presence of the above in the kwargs-parameter and can then act
		accordingly.
		"""
		return False        # by default, the IAP is not supported

	@staticmethod
	def required_parameter(asset, key):
		if key in asset.action_args:
			return asset.action_args[key]
		else:
			raise KeyError(f"Required '{key}' parameter missing.")

	@staticmethod
	def optional_parameter(asset, key, default_value=None):
		return asset.action_args.get(key, default_value)


class StatelessAction(BasicAction, ABC):
	def ctor_parameter(self):
		return {}


class StatefulAction(BasicAction, ABC):
	def __init__(self, state=None, **_):
		self.state = state if state is not None else {}

	def ctor_parameter(self):
		return {'state': self.state}


class StatelessDispatchedAction(StatelessAction, ABC):
	def execute(self, asset, context, **kwargs):
		try:
			return self._execute(**kwargs, asset=asset, context=context)
		except Exception as ex:
			return ErrorResult.from_exception(ex)

	@abstractmethod
	def _execute(self, asset, context, **kwargs):
		pass


class StatefulDispatchedAction(StatefulAction, ABC):
	def execute(self, asset, context, **kwargs):
		try:
			return self._execute(**kwargs, asset=asset, context=context)
		except Exception as ex:
			return ErrorResult.from_exception(ex)


class NoAction(StatelessAction):
	"""
	This action does nothing.
	"""
	def execute(self, asset, context):
		pass

	def get_help(self):
		return Help.make(NoAction.__doc__, None)


# -------------------------- Demo code follows - cut or comment to eof --------------------------


if __name__ == '__main__':

	def main():
		from lib.store.actions.action_tests import TestDispatchedAction
		class MockAsset:
			def __init__(self, **kwargs):
				self.action_args = kwargs


		a1 = NoAction()
		# a1 = TestAction()
		packed = a1.to_transport()
		unpacked = StatefulAction.from_transport(packed)
		print(unpacked.get_help())
		unpacked.execute(None, None)

		da1 = TestDispatchedAction()
		da1.execute(
			MockAsset(),
			None,
			# path="/some/where/out/there"),
			count=2337.0, option='X'
			# count=2337.0, option=1.1,
			# count=2337.0,
			# count=3337,
			# count=1337, label="guys",
			# count=2337, label=1500,
		)


		pass

	main()