from lib.store.asset_store import Asset
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help
from lib.store.action_registry import ActionRegistry


@ActionRegistry.store_asset(path='bin.help', user='root', group='system', mode='755')
class GetHelp(StatelessAction):
	"""
	Returns the help for an asset given its path.
	Args:
		path (str): the store-path to the asset of interest.
	"""
	def execute(self, asset: Asset, context: UpdateContext, path:str, **kwargs):
		the_asset = context.store.acquire(context, path=path)
		return the_asset.get_help()

	def get_help(self):
		return Help.from_docstring(self.__doc__)
