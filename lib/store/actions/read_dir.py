import json

from lib.path_op import TreePath
from lib.dispatcher_decorator import DispatchedNamespace
from lib.store.action import StatelessDispatchedAction
from lib.store.help import Help, Variant
from lib.value_predicate import is_of_types
from lib.store.action_registry import ActionRegistry
from lib.fsutil import apply_replacements


ReadDirScope = DispatchedNamespace()


@ActionRegistry.store_asset(path='bin.ls', user='root', group='system', mode='755')
class ReadDir(StatelessDispatchedAction):
	def get_help(self):
		return Help.make(
			"Read the contents of a directory",
			[
				Variant("json -- default output format"),
				Variant(
					"html -- html page for display in browser",
					html="any (recommended value: 1) -- if present, format output as HTML page"
				)
			],
			path="path.in.store:str | optional -- the path of the requested directory, defaults to root"
		)

	@ReadDirScope.conditional(path=is_of_types(str, list))
	def _execute(self, asset, context, path, **kwargs):
		"""
		Converts alternative tree-path formats into TreePath instances for other handlers.
		Args:
			path (str | list): path to the directory, either as a list[str|int] or tree path as a string.
		"""
		# normalize path to be of type TreePath
		return self._execute(asset, context, path=TreePath(path), **kwargs)

	@ReadDirScope.conditional()
	def _execute(self, asset, context, path: TreePath):
		"""
		Args:
			path (TreePath): path to the directory.
		"""
		contents = context.store.read_directory(context, path)
		return contents

	@ReadDirScope.conditional()
	def _execute(self, asset, context, path: TreePath, html=1):
		"""
		Args:
			path (TreePath): path to the directory.
			html (any): if present, return answer in html format.
		"""
		# {user: "user1", group: "group1", rights: "rwxr-xr-x", name: "dir1", dir: true},
		lookup = context.store.read_directory(context, path)
		# return f'<html><body><code>\n{contents}\n</code></body></html>'

		page = context.store.query(context, 'www.files', file='store_content.html')
		if page.is_error():
			return page

		icon_name = 'directory.png' if len(path) == 0 else 'directory_up.png'
		found_path = lookup['path']
		parent_path = '' if len(found_path) == 0 else str(TreePath(found_path)[:-1])

		result = apply_replacements(
			page.get_result().decode(),
			PLACEHOLDER_DIRECTORY_ICON_=f'/?asset=www.files&file=img/{icon_name}',
			PLACEHOLDER_PATH_NAME_=found_path,
			PLACEHOLDER_PARENT_NAME_=parent_path,
			PLACEHOLDER_PATH_CONTENTS_=json.dumps(lookup['contents'])
		)
		return result


	# <<Fallthrough>>
	@ReadDirScope.conditional()
	def _execute(self, asset, context, **kwargs):
		"""
		Fallthrough handler sets path to store-root.
		"""
		# No path at all? Use root:
		return self._execute(asset, context, TreePath(None), **kwargs)
