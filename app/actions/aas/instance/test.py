import base64
import json

from lib.call_result import CallResult
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help


class Test1(StatelessAction):
	def execute(self, asset:"Asset", context:UpdateContext, **kwargs):
		def _process_result(data):
			nonlocal result
			result = f'this is {data['id']} aka {base64.b64encode(data['id'].encode())}'
			pass

		result = None
		src_asset = (context.store.query(context, path='app.aas.instance.intern.58841').
		then(
			lambda r: _process_result(json.loads(r.content.decode()))
		))

		return CallResult.of(result)

	def get_help(self):
		return Help.make(
			'A test action for use by development',
			'probably nothing meaningful'
		)

