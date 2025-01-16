from typing import Any, Callable, List, Dict, Iterable, MutableSequence
from abc import ABC, abstractmethod


class Validator(ABC):
	"""Base class for all schema validators."""

	@abstractmethod
	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		pass


def _log_trace(trace, message, structure):
	if len(trace) > 0:
		trace.append(f'{message} in sub-test')
	else:
		trace.append(f'{message} on "{structure}"')


class Object(Validator):
	"""Validates dictionary structures."""

	def __init__(self, schema: Dict[str, Validator] = None, keys: Validator = None, values: Validator = None):
		self.schema = schema if schema else {}
		self.keys = keys
		self.values = values

	@staticmethod
	def _validate_all(validator: Validator, entries: Iterable[Any]):
		for entry in entries:
			if not validator.validate(entry):
				return False
		return True

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		if not isinstance(structure, dict):
			if trace is not None:
				_log_trace(trace, 'expected dict', structure)
			return False

		if self.keys is not None and not self._validate_all(self.keys, structure.keys()):
			if trace is not None:
				_log_trace(trace, f'keys validator "{self.keys}" failed', structure)
			return False

		if self.values is not None and not self._validate_all(self.values, structure.values()):
			if trace is not None:
				_log_trace(trace, f'values validator "{self.values}" failed', structure)
			return False

		for key, validator in self.schema.items():
			key_exists = key in structure
			if (
				(key_exists and not validator.validate(structure[key], trace=trace)) or
				(not key_exists and not isinstance(validator, Optional))
			):
				if trace is not None:
					_log_trace(trace, f'key "{key}" failed {validator}', structure)
				return False
		return True

	def __str__(self):
		return 'Object()'


class Array(Validator):
	"""Validates list structures."""

	def __init__(self, all: Validator = None, items: List[Validator] = None):
		if not (all or items):
			raise ValueError("Array must have either 'all' or 'items'")
		self.all = all
		self.items = items

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		if not isinstance(structure, list):
			if trace is not None:
				_log_trace(trace, 'expected list', structure)
			return False
		if self.all:
			if not all(self.all.validate(item, trace=trace) for item in structure):
				if trace is not None:
					_log_trace(trace, f'{self.all} failed', structure)
				return False
		if self.items:
			if len(structure) != len(self.items):
				if trace is not None:
					_log_trace(trace, f'expected len array of len={len(self.items)} but found len={len(structure)}', structure)
				return False
			for i, validator in enumerate(self.items):
				if not validator.validate(structure[i], trace=trace):
					if trace is not None:
						_log_trace(trace, f'{validator} failed on index {i}', structure)
					return False

		return True

	def __str__(self):
		if self.all:
			return f'Array(all={self.all})'
		else:
			return f'Array(items={self.items})'


class Type(Validator):
	"""Validates a value's type."""

	def __init__(self, expected_type: type, *other_types):
		self.expected_types = [expected_type]
		if len(other_types) > 0:
			self.expected_types.extend(other_types)

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		for expected_type in self.expected_types:
			if isinstance(structure, expected_type):
				return True

		if trace:
			_log_trace(trace, f'{self} fails', structure)

		return False

	def __str__(self):
		return f'Type({self.expected_types})'


class Value(Validator):
	"""Validates a value against a specific value."""

	def __init__(self, expected_value: Any):
		self.expected_value = expected_value

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		result = structure == self.expected_value
		if not result and trace:
			_log_trace(trace, f'not equal {self.expected_value}', structure)
		return result

	def __str__(self):
		print(f'Value({self.expected_value}:{self.expected_value.__class__.__name__})')


class Custom(Validator):
	"""Validates using a custom callable."""

	def __init__(self, func: Callable[[Any], bool]):
		self.func = func

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		result = self.func(structure)
		if not result and trace:
			_log_trace(trace, f'{self} failed', structure)
		return result

	def __str__(self):
		return f'Custom({self.func})'


class Optional(Validator):
	def __init__(self, test: Validator):
		self.test = test

	def validate(self, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
		result = self.test.validate(structure, trace=trace)
		if not result and trace:
			_log_trace(trace, f'{self} failed', structure)
		return result

	def __str__(self):
		return f'Optional({self.test})'


class Choice(Validator):
	"""
	Accepts the input if any of its validators accept it.
	"""

	def __init__(self, *validators):
		self.validators = validators

	def validate(self, structure: Any, trace: MutableSequence[str] | None = None) -> bool:
		for validator in self.validators:
			if validator.validate(structure, trace=trace):
				return True
		return False

	def __str__(self):
		return f'Choice({"|".join(self.validators)})'


def validate_structure(schema: Validator, structure: Any, trace: MutableSequence[str]|None = None) -> bool:
	"""
	Validates whether a given structure matches the provided schema.

	:param schema: The schema to validate against (an instance of Validator).
	:param structure: The structure to validate.
	:param trace: If provided, records error messages.
	:return: True if the structure matches the schema, False otherwise.
	"""
	return schema.validate(structure, trace=trace)


# <<predicate>>
def has_schema(schema, trace: MutableSequence[str]|None = None):
	def _matches(entry):
		return validate_structure(schema, entry, trace=trace)

	return _matches


# Example Usage
if __name__ == "__main__":
	def main():
		from lib.value_predicate import is_of_type, when

		schema = Object({
			"name": Type(str),
			"age": Type(int),
			"tags": Optional(Array(all=Type(str))),
			"coordinates": Array(items=[Type(int), Type(int), Type(int)]),
			"metadata": Object({
				"id": Type(int),
				# "valid": Custom(lambda x: isinstance(x, bool) and x is True)
				"valid": Custom(when(is_of_type(bool), True))
			}),
			"status": Value("active")
		})

		data = {
			"name": "Alice",
			"age": 30,
			"tags": ["python", "developer"],
			"coordinates": [10, 20, 30],
			"metadata": {
				"id": 123,
				"valid": True
			},
			"status": "active"
		}

		result = validate_structure(schema, data)
		print(result)  # Output: True

		data['metadata']['id'] = 'this should be an integer'
		# data['metadata']['valid'] = False
		trace = []
		result = validate_structure(schema, data, trace=trace)
		[print(t) for t in trace]
		print(result)  # Output: False

		pass

	main()
