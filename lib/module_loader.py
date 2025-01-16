
import importlib.util
import inspect
import sys
import os
import types
from typing import MutableMapping

from lib.project_path import SystemPath


def load_or_update_module(module, namespace:MutableMapping[str, "module"]=None):
	"""
	Load a Python module from the specified path or reload an already loaded module.

	Args:
		module (str or module): The path to the Python file to be loaded or the module object to be reloaded.
		namespace: if provided, use this namespace instead of sys.modules to store the module
			and thus do not update the regular module implementation.

	Returns:
		module: The loaded or reloaded module object.

	Raises:
		FileNotFoundError: If the specified path does not exist or is not a file.
		TypeError: If the provided object is not a valid module or module path.
		ImportError: If the requested module can not be loaded.
	"""
	def _import():
		spec = importlib.util.spec_from_file_location(module_name, module_path)
		if spec is None:
			raise ImportError(f"{module_path} can not be imported as python module.")

		module_obj = importlib.util.module_from_spec(spec)
		if module_obj is None:
			raise ImportError(f"Failed to import {module_path}.")

		if namespace:
			namespace[module_name] = module_obj
		else:
			sys.modules[module_name] = module_obj

		spec.loader.exec_module(module_obj)
		return module_obj

	if isinstance(module, str):
		# If the module is provided as a path, load or reload it
		module_path = SystemPath.local(module)
		if not os.path.isfile(module_path):
			raise FileNotFoundError(f"The specified path '{module_path}' does not exist or is not a file.")

		module_name = os.path.splitext(os.path.basename(module_path))[0]
		return _import()
	elif isinstance(module, types.ModuleType):
		# If the module is already loaded, reload it
		module_name = module.__name__
		if module_name in sys.modules:
			module_path = module.__file__
			return _import()
		else:
			raise ModuleNotFoundError(f"The module '{module_name}' is not found in sys.modules.")
	else:
		raise TypeError("The provided object is not a valid module or module path.")


def get_module(module_path):
	if module_path.endswith('.py'):
		path = module_path
		module_name = SystemPath.as_module_path(path)
	else:
		path = f'[]/{module_path.replace(".", "/")}.py'
		module_name = module_path

	if module_name in sys.modules:
		return sys.modules[module_name]
	else:
		return load_or_update_module(path)


def get_source_info(obj):
	the_class = obj if isinstance(obj, type) else obj.__class__
	source_file = SystemPath.portable(inspect.getfile(the_class))
	class_name = the_class.__name__
	return source_file, class_name


# Example usage
if __name__ == "__main__":

	class Foo:
		pass


	def main():
		from lib.store.unix_permissions import UnixPermissions
		module_path = "./nothing.py"
		# module_path = "./dist.zip"
		try:
			# Load or update the module for the first time
			# loaded_module = load_or_update_module(module_path)
			# loaded_module = get_module(module_path)
			# print(f"Module '{loaded_module.__name__}' loaded successfully.")

			x = UnixPermissions('bob', 'team')
			try:
				f = get_source_info(x)
			except Exception as ex:
				print(ex)

			# Access a function or variable from the loaded module
			if hasattr(loaded_module, 'InjectedAnnotation'):
				annotation_class = loaded_module.InjectedAnnotation
				annotated_x = annotation_class(x)
				annotated_x.set('test_entry', 'test_value')
				y = annotated_x.keys()

				pass

			# updated_module = load_or_update_module(loaded_module)
			# print(f"Module '{updated_module.__name__}' reloaded successfully.")
		except (FileNotFoundError, TypeError) as e:
			print(f"Error: {e}")

	main()
	sys.exit(0)
