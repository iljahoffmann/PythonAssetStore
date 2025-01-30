from lib.store.asset_store import Asset
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help
from lib.store.action_registry import ActionRegistry


@ActionRegistry.store_asset(path='bin.call', user='root', group='system', mode='755')
class CallAsset(StatelessAction):
	"""
	Call an asset identified by a store-path.
	Args:
		_ref (str): the store-path to the referred asset.
		other keyword arguments (Any): parameters for the asset update.
	"""
	def execute(self, asset: Asset, context: UpdateContext, _ref:str, **kwargs):
		the_asset: Asset = context.store.acquire(context, path=_ref)
		return the_asset.update(context, **kwargs).get_result()

	def get_help(self):
		return Help.from_docstring(self.__doc__)


@ActionRegistry.store_asset(
	path='www.index',
	user='root', group='system', mode='755',
	asset_args={'action_args': {'_ref': 'bin.ls', 'html': '1'}}
)
class StoreIndex(CallAsset):
	"""
	Default page when called without any asset: show root directory
	"""
	pass
