import base64
import json

from lib.path_op import path_get
from lib.call_result import CallResult
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help


class Base64Encoding(StatelessAction):
	def execute(self, asset:"Asset", context:UpdateContext, encode:str=None, decode:str=None, **kwargs):
		if encode and decode:
			raise ValueError('either encode or decode data must be provided')

		if not encode and not decode:
			raise ValueError('either encode or decode data must be provided')

		if encode:
			if isinstance(encode, str):
				result = base64.b64encode(encode.encode()).decode()
			elif isinstance(encode, bytes):
				result = base64.b64encode(encode).decode()
		else:
			missing_padding = len(decode) % 4
			if missing_padding:
				decode += '=' * (4 - missing_padding)

			if isinstance(decode, str):
				result = base64.b64decode(decode).decode()
			elif isinstance(decode, bytes):
				result = base64.b64encode(decode.decode()).decode()

		return CallResult.of(result)

	def get_help(self):
		return Help.make(
			'Convert to and from Base64 encoding',
			'The conversion result',
			encode='str - optional, the data to convert to base64 / mutually exclusive with decode',
			decode='str - optional, the data to convert from base64 / mutually exclusive with encode'
		)

