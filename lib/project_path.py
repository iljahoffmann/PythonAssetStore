import sys
import platform
import os
from lib.fsutil import path_parts, text_file_content


# []: SystemPath - base on top-level directory of a project
# [EE]: EnginePath - a component within the project - currently hard coded to be []/Testautomatisierung  (see below)
# [HOME]: UserPath - based on the users home directory


# ATTENTION
# this assumes project_path.py is located in in a direct sub-directory of engine directory
# TODO: make independent of the location within the project
base_directory_parts = path_parts(__file__)[:-2]

automation_base_parts = list(base_directory_parts)

# ATTENTION
# EnginePath is assumed a sub directory of SystemPath and it is named in the next line:
automation_base_parts.append('Testautomatisierung')
# TODO: as above: better parametrization


def parts_compare_ignore_case(parts1, parts2):
	if len(parts1) != len(parts2):
		return False

	for p1, p2 in zip(parts1, parts2):
		if p1.lower() != p2.lower():
			return False

	return True


class PortablePath:
	@staticmethod
	def portable(prefix, path):
		if path.startswith('['):
			return path

		if not os.path.isabs(path):
			_path = PortablePath.absolute(prefix, path)
		else:
			_path = path

		section = _sections[prefix]
		base = section[0]

		parts = path_parts(_path)
		# if base != parts[:len(base)]:
		if not parts_compare_ignore_case(base, parts[:len(base)]):
			raise ValueError(f"{path} is not within {prefix if len(prefix) > 0 else 'base'} directory.")

		rest = parts[len(base):]
		result = f"[{prefix}]/{'/'.join(rest)}"
		return result

	@staticmethod
	def absolute(prefix, path):
		_path = PortablePath.local(path)
		if os.path.isabs(_path):
			return _path

		section = _sections[prefix]
		base = section[0]
		result = os.path.join(*base, _path)
		result = result.replace('\\', '/')
		return result

	@staticmethod
	def relative(prefix, path):
		if path.startswith('['):
			_path = PortablePath.local(path)
		else:
			_path = path

		_path = _path.replace('\\', '/')

		if not os.path.isabs(_path):
			return _path

		section = _sections[prefix]
		if platform.system() == 'Windows':
			base = os.path.join(*section[0]).replace('\\', '/')
		elif platform.system() == 'Linux':
			base = f"/{'/'.join(section[0][1:])}"
		else:
			raise Exception(f"Platform '{platform.system()}' is not supported.")

		if not _path.startswith(base):
			raise ValueError(f"{path} is not within {prefix} directory.")

		result = _path[len(base)+1:]
		result = result.replace('\\', '/')
		return result if len(result) > 0 else '.'

	@staticmethod
	def local(path):
		if not path.startswith('['):
			return path

		parts = path.split('/')
		prefix = parts[0][1:-1]
		section = _sections[prefix]
		result = os.path.join(*section[0], *parts[1:])
		return result

	@staticmethod
	def base_directory(prefix):
		section = _sections[prefix]
		result = os.path.join(*section[0])
		result = result.replace('\\', '/')
		return result


class EnginePath:
	"""
	Convert a filename to different representations:
	- to an absolute path
	- to a relative path and
	- to and from 'portable' formats.

	With a portable path, the installation base directory on a concrete filesystem is replaced
	by an identifier that can be resolved into the equivalent path in a different base directory.

	This allows for unambiguous and transferable path definitions, that do not depend on the current
	working directory (as relative paths do).

	I.e: given the base directory of the system is located in
		/home/tester/projects/Testautomatisierung/,
	the path within that base directory
		/home/tester/projects/Testautomatisierung/lib/nothing.py
	can be converted to a system independent representation:

		portable_path = EnginePath.portable('/home/tester/projects/Testautomatisierung/lib/nothing.py')

	with portable_path resulting in '[EE]/lib/nothing.py'.

	Within another installation location (say /home/beebob/engine), this path can then be converted back to
	a valid path:

		local_path = EnginePath.local('[EE]/lib/nothing.py')

	yielding /home/beebob/engine/lib/nothing.py.

	All conversions are stable, so f.e. calling portable() on an already portable format will not change the path.

	All methods except local() will return path definitions using '/' as the path separator, while local()
	returns results using the OS path separator.
	"""
	@staticmethod
	def portable(path):
		"""
		Convert the given path to a form, that is indenpend of the installation location.
		'path' may be an absolute or relative path, where relative paths are assumed be be relative to the base.
		"""
		return PortablePath.portable('EE', path)

	@staticmethod
	def relative(path):
		"""
		Convert the given path into a path relative to the base directory.
		"""
		return PortablePath.relative('EE', path)

	@staticmethod
	def absolute(path):
		"""
		Convert the given path into an absolute path on the current installation.
		"""
		return PortablePath.absolute('EE', path)

	@staticmethod
	def local(path):
		"""
		Convert the given path into an absolute path using the OS path separator as delimiter.
		"""
		return PortablePath.local(path)

	@staticmethod
	def base_directory():
		"""
		Returns the installation's base directory.
		"""
		return PortablePath.base_directory('EE')


class SystemPath:
	@staticmethod
	def portable(path):
		return PortablePath.portable('', path)

	@staticmethod
	def relative(path):
		return PortablePath.relative('', path)

	@staticmethod
	def absolute(path):
		return PortablePath.absolute('', path)

	@staticmethod
	def local(path):
		return PortablePath.local(path)

	@staticmethod
	def base_directory():
		return PortablePath.base_directory('')

	@staticmethod
	def as_module_path(path):
		relative_path = SystemPath.relative(path)
		without_extension = relative_path[:-3] if relative_path.endswith('.py') else relative_path
		without_prefix = without_extension[2:] if without_extension.startswith('./') else without_extension
		result = without_prefix.replace('/', '.')
		return result


ProjectPath = SystemPath


class UserPath:
	@staticmethod
	def portable(path):
		return PortablePath.portable('HOME', path)

	@staticmethod
	def relative(path):
		return PortablePath.relative('HOME', path)

	@staticmethod
	def absolute(path):
		return PortablePath.absolute('HOME', path)

	@staticmethod
	def local(path):
		return PortablePath.local(path)

	@staticmethod
	def base_directory():
		return os.path.expanduser('~')


system_base_parts = list(base_directory_parts)

home_directory_parts = path_parts(UserPath.base_directory())

_sections = {
	'': (system_base_parts, SystemPath),
	'EE': (automation_base_parts, EnginePath),
	'HOME': (home_directory_parts, UserPath)
}


def read_source(sys_path, replacements=None):
	path = SystemPath.local(sys_path)
	return text_file_content(path, replacements)


if __name__ == '__main__':
	b0 = SystemPath.base_directory()
	b1 = EnginePath.base_directory()
	b2 = UserPath.base_directory()

	p = [
		'/home/tester/projects/SmartSpider/TRUNK/BBS/testsystem/Testautomatisierung/lib/nothing.py'
		# r'D:\git\Testautomatisierung\lib\nothing.py'
	]

	pU = UserPath.portable('/home/tester/IW/key.pem')

	p0 = SystemPath.portable(p[0])
	p1 = EnginePath.portable(p[0])
	try:
		p2 = EnginePath.portable('/usr/local/share')
	except Exception as ex:
		print(str(ex))

	l0 = SystemPath.local(p0)
	l1 = EnginePath.local(p1)

	r0 = SystemPath.relative(l0)
	r1 = EnginePath.relative(l0)

	l2 = EnginePath.portable(r1)

	a0 = SystemPath.absolute(r0)
	a1 = EnginePath.absolute(r1)
	p0_1 = SystemPath.portable(a0)
	p1_1 = EnginePath.portable(a1)

	p1_2 = EnginePath.portable(p1_1)
	l1_2 = EnginePath.local(l1)

	pass
