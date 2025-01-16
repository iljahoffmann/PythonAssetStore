from lib.singleton import SingletonMeta

__version__ = "0.0"


# <<JSONSerializable>> - omitted to prevent circular imports
class Nothing(metaclass=SingletonMeta):
	'''
	'nothing' is an alternative None. Using nothing allows None to be used as a valid
	expression value, distinguishable from 'operation failed' status.
	Supports serialization protocol.
	'''
	@classmethod
	def instance(cls):
		return cls()

	def to_json(self):
		return {'object_source': None}

	def code_info(self):
		return ['[]/lib/nothing.py', 'Nothing', __version__, {}]

	@classmethod
	def from_json(cls, data, version):
		return Nothing.instance()

	def __eq__(self, other):
		if type(other) == Nothing:
			return True
		return False

	def __bool__(self):
		return False


nothing = Nothing.instance()


def is_undefined(obj):
	return obj is None or obj is nothing


def is_defined(obj):
	return obj is not None and obj is not nothing
