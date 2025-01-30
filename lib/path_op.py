from typing import Callable
from collections.abc import MutableMapping, MutableSequence, Sequence
from lib.persistence import StdJSONSerializable
from lib.type_check import is_sequence
from lib.default import default_or_raise


class TreePath(StdJSONSerializable):
	def __init__(self, path, clone=False, validate_path=False, version=None):
		"""
		Initialize a TreePath from either a string, a sequence of components, or another TreePath instance.
		If a TreePath or sequence is provided, copy its components to reuse the existing parsed structure if 'clone'
		is set to True.

		Components are either strings of non-zero length as mapping keys, or integer as
		sequence indices.

		In string-representation, components are separated by dots '.' and indices are enclosed
		in square brackets, i.e.: 'home.user[15].name'.

		Args:
			path (str|TreePath|sequence[str|int]|None): the path or its components. None is an empty path.
			clone (bool): If set to True, copy components from TreePaths and sequences, else use them directly.
			validate_path (bool): if set to True, ensure types and that string-components are not empty.
		"""
		if isinstance(path, TreePath):
			self.components = path.components[:] if clone else path.components
		elif isinstance(path, str):
			self.components = self._parse_path(path)
		elif is_sequence(path):
			self.components = path[:] if clone else path
		elif path is None:
			self.components = []
		else:
			raise TypeError("TreePath constructor requires a string, a sequence, or a TreePath instance.")

		if validate_path and not all(
			[
				isinstance(c, int) or
				(isinstance(c, str) and len(c) > 0)
				for c in self.components
			]
		):
			raise ValueError(f"path contains invalid components: {path}")

	def ctor_parameter(self):
		return {'path': '.'.join(self.components)}

	def __getitem__(self, index):
		"""
		Allow index or slice access to components.
		If a slice is requested, return a new Path instance with the sliced components.
		If a single index is requested, return the corresponding component.
		Example:
		- path_instance[0] returns path_instance.components[0]
		- path_instance[:-1] returns Path(path_instance.components[:-1])
		"""
		if isinstance(index, slice):
			return TreePath(self.components[index])
		return self.components[index]

	def __setitem__(self, index, value):
		"""
		Allow setting values for specific indices or slices in components.
		Example:
		- path_instance[0] = 'new_value' sets path_instance.components[0] to 'new_value'
		- path_instance[1:3] = ['a', 'b'] sets the slice path_instance.components[1:3]
		"""
		self.components[index] = value

	def __len__(self):
		return len(self.components)

	def __add__(self, other):
		right_side = other if isinstance(other, TreePath) else TreePath(other)
		return TreePath(*self.components, *right_side.components)

	def _parse_path(self, path: str):
		"""
		Parse a path like 'company.members[0].name' into a list of steps:
		['company', 'members', 0, 'name'].
		"""
		if not path:
			return []

		parts = path.split('.')
		steps = []
		for part in parts:
			dict_key, bracket_section = self._split_first_bracket(part)
			if dict_key:
				steps.append(dict_key)
			else:
				raise ValueError("path components may not be empty")
			while bracket_section:
				idx, bracket_section = self._extract_index(bracket_section)
				steps.append(idx)
		return steps

	@staticmethod
	def _split_first_bracket(s):
		"""
		Splits s into (before_first_bracket, after_first_bracket).
		E.g. "members[0]" -> ("members", "[0]")
			 "foo[2][3]" -> ("foo", "[2][3]")
			 "company" -> ("company", "")
		"""
		bracket_pos = s.find('[')
		if bracket_pos == -1:
			return s, ""
		return s[:bracket_pos], s[bracket_pos:]

	@staticmethod
	def _extract_index(s):
		"""
		Extract integer index from a bracketed section.
		E.g. "[0][1]" -> (0, "[1]")
			 "[10]" -> (10, "")
		"""
		end_bracket = s.find(']')
		if end_bracket == -1:
			raise ValueError("Unmatched '[' in path.")
		idx_str = s[1:end_bracket]
		remainder = s[end_bracket+1:]
		return int(idx_str), remainder

	def is_empty(self):
		return len(self.components) == 0

	def parent(self):
		if len(self.components) > 0:
			return TreePath(self.components[:-1])
		return None

	def get_from(self, json, default=None, stack=None):
		return path_get(json, self, default=default, stack=stack)

	@staticmethod
	def join(*args, validate_path=False):
		"""
		Concatenate paths into a new joined path.
		Args:
			*args (Sequence[str|container|TreePath]): the paths to be joined in all possible representations.
			validate_path (bool): if True, validate the joined path for correctness (type and non-zero length) and
				raise ValueError on failure.
		Example:
			- join 4 paths and convert to string:
			str(TreePath.join('a[0].b', ['c', 0], TreePath('d'), 'e')) -> 'a[0].b.c[0].d.e'
			- empty path
			TreePath.join().is_empty()	-> True
		"""
		joined_components = [c for arg in args for c in TreePath(arg).components]
		return TreePath(joined_components, validate_path=validate_path)

	def __repr__(self):
		return f'TreePath({self.components})'

	def __str__(self):
		parts = []
		for i, c in enumerate(self.components):
			if isinstance(c, int):
				parts.append(f'[{c}]')
			else:
				if i > 0:
					parts.append('.')
				parts.append(c)

		return ''.join(parts)


def path_get(
		root:object,
		path,
		default=None,
		stack:MutableSequence[object]=None,
		abort_condition:Callable[[object], bool]=None
):
	"""
	Retrieve the value at the given path from the root structure.
	If any part of the path does not exist, return default (or raise if default is an Exception).

	Args:
		root (json): the root node of the JSON structure.
		path (str|TreePath|Sequence[str]|None): the requested path. None equals root.
		default (object|Exception): if present and path is not found, return value if not an exception, else raised.
		stack (MutableSequence[object]): if present, records visited nodes by appending to the stack.
		abort_condition (Callable[[json node], bool]): if present, called with current node; if it returns True: stop
			the descent and return current node

	Returns:
		object: the result of the lookup or 'default', if an error occurred and default is not an exception.

	Raises:
		default, if default is an exception: -on path component not found / -on type mismatch
	"""
	tree_path = TreePath(path)
	current = root
	if stack:
		stack.append(current)

	for step in tree_path.components:
		if abort_condition and abort_condition(current):
			return current

		if isinstance(step, str):
			# Dictionary key lookup
			if not isinstance(current, MutableMapping) or step not in current:
				return default_or_raise(default)
		elif isinstance(step, int):
			# List index lookup
			if not isinstance(current, MutableSequence) or step < 0 or step >= len(current):
				return default_or_raise(default)
		else:
			return default_or_raise(default)

		try:
			current = current[step]
		except (KeyError, IndexError):
			return default_or_raise(default)

		if stack:
			stack.append(current)

	return current


def path_set(
		root: object,
		path,
		value,
		default_getter: Callable[[object, object], None]=None,
		node_created_hook: Callable[[object, object], None] = None
):
	"""
	Set the value at the given path in the root structure.
	Create intermediate dictionaries or lists as needed.
	Extend lists if out-of-range indices are requested.

	Args:
		root (json): the JSON structure in which the set is performed.
		path (str|TreePath|Sequence[str]): the requested path. Root can not be set (KeyError).
		value (object): the assigned value.
		default_getter (Callable(json-container, json-key-or-index)): optional - if present called to obtain new
			container instances before insertion.
		node_created_hook (Callable(json-container, json-key-or-index)): optional - if present gets called with the
			container and the key within it, for that a new intermediate container was constructed in container[key].
	"""
	def _handle_mapping_step():
		nonlocal current

		if not isinstance(current, MutableMapping):
			raise TypeError("path_set: expected a dict for a dictionary key step, but got something else.")

		if is_last:
			current[step] = default_getter(current, step)

			if node_created_hook:
				node_created_hook(current, step)
		else:
			next_step = tree_path.components[i + 1]
			if isinstance(next_step, str):
				# Next step is a dict key
				if step not in current or not isinstance(current[step], MutableMapping):
					current[step] = default_getter(current, next_step)
			elif isinstance(next_step, int):
				# Next step is a list index
				if step not in current or not isinstance(current[step], MutableSequence):
					current[step] = default_getter(current, next_step)
			else:
				raise TypeError(f"path_set: invalid path component '{next_step}'.")

			if node_created_hook:
				node_created_hook(current, step)

			current = current[step]
	# ---

	def _handle_sequence_step():
		nonlocal current

		idx = step
		if not isinstance(current, MutableSequence):
			raise TypeError(f"path_set: expected a list for a list index step, but got {current.__class__} at index {i}.")

		# Extend the list if out-of-range
		if idx >= len(current):
			current.extend([None] * (idx - len(current) + 1))

		if is_last:
			current[step] = default_getter(current, step)

			if node_created_hook:
				node_created_hook(current, idx)
		else:
			next_step = tree_path.components[i + 1]
			if isinstance(next_step, str):
				# Need a dict at current[idx]
				if current[idx] is None or not isinstance(current[idx], MutableMapping):
					current[idx] = default_getter(current, next_step)
			elif isinstance(next_step, int):
				# Need a list at current[idx]
				if current[idx] is None or not isinstance(current[idx], MutableSequence):
					current[idx] = default_getter(current, next_step)
			else:
				raise KeyError(f'"{next_step}" is neither int nor str in "{tree_path.__repr__()}"')

			if node_created_hook:
				node_created_hook(current, step)

			current = current[idx]
	# ---

	def _default_default_getter(container, key):
		if is_last:
			# value gets assigned last
			return value    # same as container[key], but can be accessed here in the outer scope

		# intermediate storage created
		if isinstance(key, str):
			return {}
		else:
			return []

	if default_getter is None:
		default_getter = _default_default_getter

	tree_path = TreePath(path)
	if not tree_path.components:
		raise KeyError(f'can not set values for an empty path')

	current = root
	for i, step in enumerate(tree_path.components):
		is_last = (i == len(tree_path.components) - 1)

		if isinstance(step, str):
			# Dictionary key step
			_handle_mapping_step()
		elif isinstance(step, int):
			# List index step
			_handle_sequence_step()
		else:
			raise KeyError(f'"{step}" is neither int nor str in "{tree_path.__repr__()}"')


def path_del(root, path, default=None):
	"""
	Delete the value at the given path and return it.
	If path leads to a dict key, remove the key.
	If it leads to a list index, pop the element.
	If it doesn't exist, return (or raise) the default.
	"""
	tree_path = TreePath(path)
	if not tree_path.components:
		# Nothing to delete at root level
		return default_or_raise(default)

	current = root
	for i, step in enumerate(tree_path.components):
		is_last = (i == len(tree_path.components) - 1)
		if is_last:
			# Perform deletion
			if isinstance(step, str):
				# Dict deletion
				if not isinstance(current, MutableMapping) or step not in current:
					return default_or_raise(default)
				val = current.pop(step)
				return val
			else:
				# List deletion
				idx = step
				if not isinstance(current, MutableSequence) or idx < 0 or idx >= len(current):
					return default_or_raise(default)
				val = current.pop(idx)
				return val
		else:
			# Navigate deeper
			if isinstance(step, str):
				if not isinstance(current, MutableMapping) or step not in current:
					return default_or_raise(default)
				current = current[step]
			else:
				idx = step
				if not isinstance(current, MutableSequence) or idx < 0 or idx >= len(current):
					return default_or_raise(default)
				current = current[idx]


def path_iter(root:object, path, on_miss: Callable[["_PathIterator"], object]=None):
	"""
	Descents into a json structure along a path via iterator that yields every node encountered on traversal.

	Args:
		root (json): the root node of the JSON structure.
		path (str|TreePath|Sequence[str]|None): the requested path. None equals root.
		on_miss (Callable[[_PathIterator], object]): if present, is called when component is not found.
			If on_miss returns a non-None value, it is used as the new current node.
			When called, this_PathIterator.components[this_PathIterator.index] lookup failed on
			this_PathIterator.current.

	Returns:
		iterator: yields nodes encountered on descent
	"""
	class _PathIterator:
		def __init__(self):
			self.current = root
			self.index = -1
			self.components = tree_path.components

		def __iter__(self):
			return self

		def __next__(self):
			self.index += 1
			if self.index >= len(self.components):
				raise StopIteration()

			to_lookup = self.components[self.index]
			if on_miss:
				lookup = path_get(self.current, [to_lookup], default=not_found)

				if lookup is not_found:
					lookup = on_miss(self)

				if lookup is None:
					raise KeyError(f'"{to_lookup}" not found at index {self.index}')

				self.current = lookup
			else:
				self.current = path_get(
					self.current,
					[to_lookup],
					default=KeyError(f'"{to_lookup}" not found at index {self.index}')
				 )
			return self.current

	not_found = object()
	tree_path = TreePath(path)
	return _PathIterator()
