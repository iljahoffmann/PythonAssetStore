from lib.store.action_registry import ActionRegistry
from lib.store.action import StatelessAction
from lib.store.help import Help


@ActionRegistry.store_asset(path='test.active')
class TestActiveAction(StatelessAction):
	"""
	Test action for inner-access-protocol.

	Args:
		inner get (Any): accepted.

	Returns:
		Any: all arguments, including inner get arg.
	"""
	def execute(self, asset, context, **kwargs):
		return kwargs

	def get_help(self):
		return Help.from_docstring(self.__doc__)

	def accepts_inner_access(self):
		return True
