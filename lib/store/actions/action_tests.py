from lib.dispatcher_decorator import DispatchedNamespace
from lib.value_predicate import *
from lib.module_loader import get_source_info
from lib.call_result import ErrorResult

from lib.store.action import StatelessAction, StatelessDispatchedAction
from lib.store.help import Help

# ----------- Basic Action ---------------------------------------------------------------
class TestAction(StatelessAction):
	def execute(self, asset, context, **kwargs):
		m = 'Hello Action No5'
		print(m, kwargs)
		return m

	def get_help(self):
		return Help.make('an action to take basic test actions', 'None', args='nope. no args.')


# ----------- Action with multi-dispatch and pre-conditions ------------------------------
TestDispatchedActionScope = DispatchedNamespace()


class TestDispatchedAction(StatelessDispatchedAction):
	@TestDispatchedActionScope.conditional()
	def _execute(self, asset, context, path: str, **kwargs):
		return f'some path here: {path}'

	@TestDispatchedActionScope.conditional(
		count=when(is_a(int), in_range(1000, 3000))
	)
	def _execute(self, asset, context, count, **kwargs):
		return f'got a good count: {count}'

	@TestDispatchedActionScope.conditional(
		option=optional(is_a(str))
	)
	def _execute(self, asset, context, count: float, option='', **kwargs):
		f = get_source_info(self)
		return f'floaty option5: {count}/{option} ---- {kwargs}'

	@TestDispatchedActionScope.conditional()
	def _execute(self, asset, context, count: float):
		return f'thats floaty: {count}'

	@TestDispatchedActionScope.conditional()
	def _execute(self, asset, context, count: int):
		return f'got a count: {count}'

	@TestDispatchedActionScope.conditional(
		count=in_range(1000, 3000)
	)
	def _execute(self, asset, context, count: int, label: int):
		return f'got a count and a max: {count}/{label}'

	@TestDispatchedActionScope.conditional()
	def _execute(self, asset, context, count: int, label: str):
		return f'got a count with a label: {count} "{label}"'

	@TestDispatchedActionScope.conditional()
	def _execute(self, asset, context, **kwargs):
		error = 'TestDispatchedAction: Fallthrough method called -- no appropriate handler was found.'
		lines = [error, 'Args:', *[f'{k}:{v.__class__.__name__}={v}' for k, v in kwargs.items()]]
		return ErrorResult('\n'.join(lines))

	def get_help(self):
		return Help.make(
			'an action to take basic dispatched actions',
			'None',
			asset='the active Asset (do not set, provided by update)',
			context='the UpdateContext (do not set, provided by update)',
			count='int | float -- some number / "good" between 1000 and 3000',
			label='int | str -- more data',
			optional='str, optional if count:float (default="") -- and even more data'
		)
