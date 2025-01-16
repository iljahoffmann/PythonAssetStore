from lib.path_op import TreePath
from lib.dispatcher_decorator import DispatchedNamespace
from lib.store.action import StatelessDispatchedAction
from lib.store.help import Help, Variant
from lib.value_predicate import is_of_types

ReadDirScope = DispatchedNamespace()


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
		# normalize path to be of type TreePath
		return self._execute(asset, context, path=TreePath(path), **kwargs)

	@ReadDirScope.conditional()
	def _execute(self, asset, context, path: TreePath):
		contents = context.store.read_directory(context, path)
		return contents

	@ReadDirScope.conditional()
	def _execute(self, asset, context, path: TreePath, html=1):
		contents = context.store.read_directory(context, path)
		return f'<html><body><code>\n{contents}\n</code></body></html>'

	# <<Fallthrough>>
	@ReadDirScope.conditional()
	def _execute(self, asset, context, **kwargs):
		# No path at all? Use root:
		return self._execute(asset, context, TreePath(None), **kwargs)
