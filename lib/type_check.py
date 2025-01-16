from collections.abc import Mapping, Sequence


def is_sequence(obj):
	"""
	Check if the object is a sequence but not a string, bytes, or bytearray.

	Args:
	obj (object): The object to be checked.

	Returns:
	bool: True if the object is a sequence but not a string, bytes, or bytearray. False otherwise.
	"""
	return isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray))


def is_mapping(obj):
	return isinstance(obj, Mapping)


def is_container(obj):
	return is_mapping(obj) or is_sequence(obj)