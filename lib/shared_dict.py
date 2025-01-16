class SharedDict(dict):
	"""
	A dictionary that redirects all read/write accesses to an externally
	provided dictionary shared by all instances or consumers.
	Note: SharedDict by itself can not be persistent, because the origin of the target is unknown.
	"""

	def __init__(self, shared_dict, *args, **kwargs):
		# Although we're inheriting from dict, we don't want to store data in self.
		# Instead, keep a reference to the shared_dict provided.
		super().__init__()  # Initialize the base class (creates an empty dict internally).
		self._shared = shared_dict

		# Optionally, you can populate the shared_dict with initial data
		# from *args, **kwargs if that's desired:
		self.update(*args, **kwargs)

	def __getitem__(self, key):
		return self._shared[key]

	def __setitem__(self, key, value):
		self._shared[key] = value

	def __delitem__(self, key):
		del self._shared[key]

	def __contains__(self, key):
		return key in self._shared

	def __iter__(self):
		return iter(self._shared)

	def __len__(self):
		return len(self._shared)

	def clear(self):
		self._shared.clear()

	def copy(self):
		"""
		Return a shallow copy of the *shared dictionary*, not the SharedDict wrapper itself.
		Note: If you truly want an independent copy, you might want to do a deeper copy.
		"""
		return self._shared.copy()

	def get(self, key, default=None):
		return self._shared.get(key, default)

	def items(self):
		return self._shared.items()

	def keys(self):
		return self._shared.keys()

	def pop(self, key, default=None):
		return self._shared.pop(key, default)

	def popitem(self):
		return self._shared.popitem()

	def setdefault(self, key, default=None):
		return self._shared.setdefault(key, default)

	def update(self, *args, **kwargs):
		return self._shared.update(*args, **kwargs)

	def values(self):
		return self._shared.values()

	def __repr__(self):
		# Show that this dict is a view of another dictionary
		return f"{self.__class__.__name__}({repr(self._shared)})"
