from abc import ABC
from lib.call_result import ErrorResult
from lib.dispatcher_decorator import DispatchedNamespace
from lib.store.action_registry import ActionRegistry
from lib.store.action import StatelessAction
from lib.store.help import Help


class DispatchToMemberAction(StatelessAction, ABC):
	"""
	Use 'method' or _inner_get as member-method name and dispatch to it if available.
	"""
	def execute(self, asset, context, method:str=None, **kwargs):
		handler_name = method if method else str(kwargs.get('_inner_get', '_invalid_method'))
		if len(handler_name) == 0:
			raise ValueError('method name missing - either provide a "method" or use inner access')

		handler = getattr(self, handler_name)

		try:
			return handler(**kwargs, asset=asset, context=context)
		except Exception as ex:
			return ErrorResult.from_exception(ex)

	def _invalid_method(self, method_name):
		raise ValueError(f'no such method: "{method_name}"')

	def accepts_inner_access(self):
		return True


TestDispatchNamespace = DispatchedNamespace()


@ActionRegistry.store_asset(path='test.gimme')
class TestDispatchToMember(DispatchToMemberAction):
	"""
	Test class for DispatchToMemberAction: offers 'foo()' and 'bar()', 'baz(x)' and 'sum(a, b[, c])'.
	"""
	def __init__(self):
		self._member_value = 17

	@staticmethod
	def foo(asset, context, **kwargs):
		result = f'foo ({kwargs})'
		return result

	def bar(self, asset, context, **kwargs):
		result = f'bar - val={self._member_value} ({kwargs})'
		return result

	def baz(self, asset, context, x, **kwargs):
		result = f'baz - val/x={self._member_value/int(x)} ({kwargs})'
		return result

	@TestDispatchNamespace.conditional()
	def sum(self, asset, context, a, b, c, **kwargs):
		result = f'sum3: {a}+{b}+{c} = {int(a)+int(b)+int(c)}'
		return result

	@TestDispatchNamespace.conditional()
	def sum(self, asset, context, a, b, **kwargs):
		result = f'sum2: {a}+{b} = {int(a)+int(b)}'
		return result

	def get_help(self):
		return Help.from_docstring(self.__doc__)
