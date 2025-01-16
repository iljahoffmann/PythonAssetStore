import base64
import json

from lib.path_op import path_get
from lib.call_result import CallResult
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help


class JsonFormat(StatelessAction):
	def _get_handler(self, source):
		update_class = source.__class__.__name__
		handler = getattr(self, f'_{update_class}', self._unknown)
		return handler

	def execute(self, asset:"Asset", context:UpdateContext, path:str, key=None, **kwargs):
		def _process_result(data):
			nonlocal result
			result = f'this is {data['id']} aka {base64.b64encode(data['id'].encode())}'
			pass

		update_result = context.store.query(context, path=path).get_result()
		handler = self._get_handler(update_result)
		result = handler(asset, context, key, update_result)

		return CallResult.of(result)

	def _Response(self, asset, context, key, update_result):
		data = json.loads(update_result.content.decode())
		if key is None:
			return data
		else:
			result = path_get(data, key)
			return result

	def _ValidResult(self, asset, context, key, update_result):
		data = update_result.get_result()
		handler = self._get_handler(data)
		result = handler(asset, context, key, data)
		return result

	def _unknown(self, asset, context, key, update_result):
		raise ValueError(f'Unhandled data type: {update_result.__class__.__name__}')

	def get_help(self):
		return Help.make(
			'Access JSON-valued assets by TreePaths',
			'The sub-structure selected by "key"',
			path='str - path to the source asset',
			key='str - defaults to root element'
		)

