# A value predicate is a function(value..) -> bool with 'consistent results'.
#
# 'Consistent results' means, the function will yield the same result every time
# it is called with one specific value. This property is required to be able
# to predict a predicate's behaviour for a value that already had been tested.
#
# Higher-order predicates assume value(s) to be of type predicate and thus
# are chainable (tagged by <<Combinator>> stereotype).

import re
from lib.type_check import is_sequence, is_mapping


def description(predicate):
	"""
	Helper to obtain a more readable description from predicates
	"""
	try:
		return predicate.__str__()
	except TypeError:
		return str(predicate)


def predicate_matches(predicate, value):
	if callable(predicate):
		return predicate(value)
	else:
		return predicate == value


# <<Predicate>>
def any_(_):
	return True


# <<Predicate>>
def not_none(value):
	return value is not None


# <<Predicate>>
def contains(value):
	searched = value
	result = when(lambda _v: searched in _v)
	setattr(result, '__str__', lambda: f'contains({description(searched)})')
	return result


# <<Predicate>>
def is_from(values):
	result = when(lambda _v: _v in values)
	setattr(result, '__str__', lambda: f'is_in([{", ".join(map(lambda _v: description(_v), values))}])')
	return result


# <<Predicate>>
# explicit version of value compare as a predicate
def value_equals(expected_value):
	def _match(value):
		return value == expected_value

	setattr(_match, '__str__', lambda: f'value_equals({expected_value})')
	return _match


# <<Predicate>>
def starts_width(value):
	# searched = StringBase.ID(value)
	searched = value
	result = when(lambda _v: _v.startswidth(searched))
	setattr(result, '__str__', lambda: f'starts_with({description(searched)})')
	return result


# <<Predicate>> <<Combinator>>
def not_(predicate):
	def _match(value):
		return not predicate_matches(predicate, value)
	setattr(_match, '__str__', lambda: f'starts_with({description(predicate)})')
	return _match


# <<Predicate>> <<Combinator>>
def when(*predicates):      # logical and of predicates
	def _match(value):
		for predicate in predicates:
			if not predicate_matches(predicate, value):
				return False
		return True
	setattr(_match, '__str__', lambda: f'when([{" and ".join(map(lambda _v: description(_v), predicates))}])')
	return _match


# <<Predicate>> <<Combinator>>
def either(*predicates):    # logical or of predicates
	def _match(value):
		for predicate in predicates:
			if predicate_matches(predicate, value):
				return True
		return False
	setattr(_match, '__str__', lambda: f'either([{" or ".join(map(lambda _v: description(_v), predicates))}])')
	return _match


# <<Predicate>> <<Combinator>>
def one_of(*predicates):    # logical xor of predicates
	def _match(value):
		match_found = False
		for predicate in predicates:
			if predicate_matches(predicate, value):
				if match_found:
					return False    # already got one match
				match_found = True
		return match_found
	setattr(_match, '__str__', lambda: f'one_of([{" or ".join(map(lambda _v: description(_v), predicates))}])')
	return _match


# <<Predicate>>
def is_of_type(*types):
	def _match(value):
		for t in types:
			if isinstance(value, t):
				return True
		return False
	setattr(_match, '__str__', lambda: f'is_of_type([{" or ".join(map(lambda _v: description(_v), types))}])')
	return _match


# <<Predicate>>
def is_of_types(*types):       # for smoother spelling only
	return is_of_type(*types)


# <<Predicate>>
def is_list():
	def _match(value):
		return is_sequence(value)

	return _match


# <<Predicate>>
def is_dict():
	def _match(value):
		return is_mapping(value)

	return _match


# <<Predicate>>
# Python may load modules in different name-spaces as distinct instances, in
# which cases isinstance() -and thus is_of_type()- may not be able to defer the intended relationship.
# is_a() is slower, as it compares the module's and the class name, but will match
# types from different namespaces. It is safe to use is_of_type() for basic types.
def is_a(*types):
	# value.__class__.__mro__
	def _same(_a, _b):
		return _a.__name__ == _b.__name__ and _a.__module__ == _b.__module__

	def _isinstance(_mro, _b_class):
		for _class in _mro:
			if _same(_class, _b_class):
				return True
		return False

	def _match(value):
		mro = value.__class__.__mro__
		for t in types:
			if _isinstance(mro, t):
				return True
		return False

	setattr(_match, '__str__', lambda: f'is_a([{" or ".join(map(lambda _v: description(_v), types))}])')
	return _match


# <<Predicate>>
def has_key_value(**kwargs):
	def _match(value):
		if not isinstance(value, dict):
			return False

		for k, v in kwargs.items():
			if k not in value:
				return False
			in_value = value[k]
			if not predicate_matches(v, in_value):
				return False

		return True
	setattr(_match, '__str__', lambda: f'has_key_value({", ".join(map(lambda _k, _v: f"{_k}={description(_v)}", kwargs.items()))})')
	return _match


# <<Predicate>>
def match(pattern, **kwargs):
	def _match(value):
		m = p.match(value)
		return m is not None

	p = re.compile(pattern, **kwargs)
	setattr(_match, '__str__', lambda: f'match({pattern}])')
	return _match


# <<Predicate>>
def has_attr(attr_name):
	def _match(value):
		attr = getattr(value, attr_name, None)
		return attr is not None

	setattr(_match, '__str__', lambda: f'has_attr({attr_name}])')
	return _match


# <<Predicate>>
def of_len(length, _upper=None):
	def _match_range(value):
		return length <= len(value) <= _upper

	def _max_len(value):
		return len(value) <= length

	def _min_len(value):
		return length <= len(value)

	if _upper is None:
		result = _max_len
	else:
		if _upper == -1:
			result = _min_len
		else:
			result = _match_range

	setattr(result, '__str__', lambda: f'of_len(min={length}, max={_upper})')
	return result


has_index = lambda v: has_attr('__getitem__')(v)


has_iter = lambda v: either(has_attr('__iter__'), has_attr('__next__'))(v)


def at(index, predicate):
	def _match(value):
		if not has_index(value):
			return False
		if isinstance(index, int) and index >= len(value):
			return False
		elif index not in value:
			return False

		return predicate_matches(predicate, value[index])

	setattr(_match, '__str__', lambda: f'at({index}: {description(predicate)})')
	return _match


def is_in(indexable):
	def _never(_):
		return False

	def _match(value):
		_result = value in indexable
		return _result

	if not has_index(indexable):
		result = _never
		setattr(result, '__str__', lambda: f'is_in({indexable})')
	else:
		result = _match
		setattr(result, '__str__', lambda: f'is_in([{", ".join(map(lambda _v: description(_v), indexable))}])')

	return result


def in_range(min_value=None, max_value=None):
	def _match(value):
		if min_value is not None and value < min_value:
			return False

		if max_value is not None and max_value < value:
			return False

		return True

	setattr(_match, '__str__', lambda: f'in_range(min_value={min_value}, max_value={max_value})')
	return _match


# <<predicate>>
def member_matches(member_name, predicate):
	def _match(value):
		member = getattr(value, member_name, None)
		if member is None:
			return False
		return predicate_matches(predicate, member)
	return _match


# <<predicate>>
# currently, this pred checks for method names only - a proper impl would check the params too - or not?
# Problem here is: the method could be dispatched, and maybe can/should not be identified
def implements(interface_instance):
	def _match(value):
		value_methods = {
			attr for attr in dir(value)
			if callable(getattr(value, attr)) and not attr.startswith('_')
		}

		missing = interface_methods - value_methods
		return len(missing) == 0

	interface_methods = {
		attr for attr in dir(interface_instance)
		if callable(getattr(interface_instance, attr)) and not attr.startswith('_')
	}
	return _match


def call(predicate_function, *args, **kwargs):
	"""
	Wrap a predicate function to act as a value_predicate.
	The predicate_function can be provided with args and kwargs but must accept
	the value as its first positional parameter.
	:param predicate_function: predicate_function(value, *args, **kwargs) -> bool
	:return: reference to the test function receiving the value
	"""
	def _match(value):
		return predicate_function(value, *args, **kwargs)

	return _match


def optional(predicate):
	"""Use in conjunction with dict_predicate(): considered True, when the key is missing, but has to match
	'predicate' if the key is present"""
	def _match_optional_condition(value):
		return predicate(value)

	setattr(_match_optional_condition, '__str__', lambda: f'optional({description(predicate)})')
	return _match_optional_condition


def not_present():
	"""Use in conjunction with dict_predicate(): considered True only when the key is missing"""
	def _match_optional_condition(value):
		return False

	return _match_optional_condition


def is_optional_predicate(predicate):
	return predicate.__name__ == '_match_optional_condition'


def dict_predicate_error(**kwargs):
	def _match(value):
		if not isinstance(value, dict):
			return "value is not a dict"

		for name, condition in kwargs.items():
			if name not in value:
				# if condition.__name__ == '_match_optional_condition':
				if is_optional_predicate(condition):
					continue
				return f"'{name}' is a missing key"

			entry = value[name]
			if not predicate_matches(condition, entry):
				return f"test for '{name}' failed on '{entry}'"

		return None

	return _match


def dict_predicate(**kwargs):
	"""
	Assumes value to be a dict. For all kwargs: each key must be contained in the dict (except the condition is
	'optional()') and kwargs[key](the_dict[key]) must return true for the final result to yield True.
	This allows to define tests to be applied to the dict, by providing keyword arguments, where the name of the
	parameter is tried as a dict key, and the parameters value is used as the test function for dict[key].
	(see example in module's main - use dumped_dict_predicate() to print debug messages for failed tests)
	:param kwargs:
	:return: f, where f(value) -> bool
	"""
	def _match(value):
		error_result = impl(value)
		return error_result is None

	impl = dict_predicate_error(**kwargs)
	return _match


def dumped_dict_predicate(**kwargs):
	"""
	Debug: like dict_predicate() but prints the failing condition on the console
	:param kwargs:
	:return: same as dict_predicate_error(**kwargs)
	"""
	def _match(value):
		error_result = impl(value)
		if error_result:
			print(error_result)
		return error_result is None

	impl = dict_predicate_error(**kwargs)
	return _match


if __name__ == '__main__':
	class Foo:
		def print(self):
			pass

	class Bar:
		def print(self):
			pass

		def baz(self):
			pass

	_f = Foo()
	_b = Bar()

	_m1 = implements(Foo)(_b)
	_m2 = implements(Bar)(_f)

	_message = {
		'pdu': 'login',
		'meta': {},
		'args': {
			'x': 17,
			'y': 1
		}
	}

	def equals_17(value, *args, **kwargs):
		return value == 17

	_p = dumped_dict_predicate(
		pdu='login',
		# meta=optional(is_of_type(dict)),
		meta=not_present(),
		args=dumped_dict_predicate(x=call(equals_17, info='add. info'))
	)
	_message_complies_to_predicate = _p(_message)

	_pred1 = contains('hello')
	_pred2 = contains('hello')
	_same = _pred1 == _pred2
	pass

