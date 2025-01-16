import os
import magic

from lib.project_path import ProjectPath
from lib.call_result import ErrorResult
from lib.store.action import StatefulAction


class FileDirectory(StatefulAction):
	def set_base_path(self, base_path:str):
		self.state['base'] = base_path
		return self

	def execute(self, asset, context, file:str, **kwargs):
		base_dir = ProjectPath.local(self.state['base'])
		full_path = os.path.join(base_dir, file)
		if not os.path.exists(full_path):
			return ErrorResult(f'file not found: {file}')

		context['mimetype'] = magic.from_file(full_path)
		with open(full_path, 'rb') as f:
			try:
				result = f.read()
			except Exception as ex:
				print(ex)
				return ErrorResult.from_exception(ex)

			return result

	def get_help(self):
		pass