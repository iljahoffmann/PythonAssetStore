import sys
import traceback
from abc import ABC, abstractmethod
from lib.default import default_or_raise
from lib.persistence import IPersistentObject, BasicPersistentObject


# <<monad>>
class CallResult(IPersistentObject, ABC):
	"""
	Encapsulates the result of a function call, that either yielded a ValidResult or produced an ErrorResult.

	Base class for all call results. Persistence is not available for ValidResults with non-serializable value.
	"""

	@staticmethod
	def of(value):
		"""
		Generic constructor for the monad:
		creates an instance of ValidResult with assigned 'value', except the provided value is an ErrorResult,
		in which case it is returned unmodified. This allows for result chaining.
		"""
		if isinstance(value, ErrorResult):
			return value
		elif isinstance(value, Exception):
			return ErrorResult.from_exception(value)
		else:
			return ValidResult(value)

	@abstractmethod
	def then(self, func, *args, **kwargs):
		"""
		Applies the given function to the result if it is valid.
		Propagates the error otherwise, capturing exceptions and stack traces.
		(This method is often called 'bind' in the context of monads.)

		Args:
			func (Callable[[object, *args, **kwargs], CallResult]): the callback function on ValidResults, receiving the
			 real value as its first parameter. Ignored on ErrorResults.
			*args, **kwargs: additional callback parameter.
		"""
		pass

	@abstractmethod
	def on_error(self, func, *args, **kwargs):
		"""
		The logical negation of then(): the given function is called on ErrorResults only.
		I.e.: "get_some_call_result().then(process_it).on_error(notify_fail)" resembles an if-then-else construct.

		Args:
			func (Callable[[ErrorResult, *args, **kwargs], None]): the callback function on ErrorResults, receiving the
				ErrorResult as its first parameter. Ignored on ValidResults.
			*args, **kwargs: additional callback parameter.
		"""
		pass

	@abstractmethod
	def get_result(self, default=None):
		"""
		Returns the effective value of a ValidResult, or the default value on an ErrorResult.
		"""
		pass

	@abstractmethod
	def is_error(self):
		pass

	def is_valid(self):
		return not self.is_error()


class ValidResult(CallResult, BasicPersistentObject):
	"""
	Represents a successful result.
	"""
	def __init__(self, value):
		"""
		ATTENTION: use CallResult.of(some_value) to create instances: that static method checks for ErrorResults
					as a value too and acts accordingly.
		"""
		if isinstance(value, ValidResult):
			# prevent instance nesting
			self._value = value.get_result()
		else:
			# An ErrorResult can be the value of an ValidResult
			self._value = value

	def ctor_parameter(self):
		return {'value': self._value}

	def is_error(self):
		return False

	def then(self, func, *args, **kwargs):
		try:
			return CallResult.of(func(self.get_result(), *args, **kwargs))
		except Exception as e:
			return ErrorResult.from_exception(e)

	def on_error(self, func, *args, **kwargs):
		# not an error - continue
		return self

	def get_result(self, default=None):
		"""
		Returns the encapsulated value.
		"""
		return self._value

	def __repr__(self):
		return f"ValidResult[{self._value.__class__.__name__}]({self._value})"

	def dump(self, stream=None):
		"""
		Dumps the error message and stack trace to the provided stream or stdout.
		"""
		if stream is None:
			stream = sys.stdout
		print(self.__repr__(), file=stream)


class ErrorResult(CallResult, BasicPersistentObject):
	"""
	Represents an error result, containing an exception and its stack trace.
	"""
	def __init__(self, error_message=None, exception=None, stack_trace=None, prior_error=None):
		self.error_message = error_message
		self.exception = exception
		self.stack_trace = stack_trace
		self.prior_error = prior_error

	def ctor_parameter(self):
		return {
			'error_message': self.error_message,
			'exception': str(self.exception),
			'stack_trace': str(self.stack_trace),
			'prior_error': self.prior_error
		}

	def is_error(self):
		return True

	def then(self, func, *args, **kwargs):
		# do nothing, chain on
		return self

	def on_error(self, func, *args, **kwargs):
		try:
			return CallResult.of(func(self, *args, **kwargs))
		except Exception as e:
			return ErrorResult.from_exception(e, prior_error=self)

	@classmethod
	def from_exception(cls, exception, message=None, prior_error=None):
		"""
		Creates an ErrorResult from an exception, capturing the stack trace.
		"""
		error_message = str(exception)
		if message is not None:
			error_message = f"{message}: {error_message}"
		stack_trace = traceback.format_exc().split('\n')
		return cls(error_message, exception, stack_trace, prior_error=prior_error)

	def get_error_message(self):
		"""
		Returns the error message.
		"""
		return self.error_message

	def get_exception(self):
		"""
		Returns the stored exception object.
		"""
		return self.exception

	def get_stack_trace(self):
		"""
		Returns the formatted stack trace.
		"""
		return self.stack_trace

	def get_result(self, default=None):
		"""
		Returns the default value as ErrorResult has no valid value.

		Args:
			default (Any|Exception|ErrorResult):
				- if default is an Exception, the exception is raised
				- if default is the type ErrorResult, this ErrorResult instance is returned
				- in all other cases, 'default' is returned as a value
		"""
		if default is ErrorResult:
			return self

		return default_or_raise(default_value=default, message='ErrorValue encountered')

	def dump(self, stream=None):
		"""
		Dumps the error message and stack trace to the provided stream or stdout.
		"""
		if stream is None:
			stream = sys.stdout
		print(f"Error: {self.error_message}", file=stream)
		print("Stack Trace:", file=stream)
		print(self.get_stack_trace(), file=stream)

	def as_json(self):
		return {
			'message': self.error_message,
			'exception': str(self.exception) if self.exception else None,
			'stacktrace': self.get_stack_trace()
		}

	def __repr__(self):
		return f"ErrorResult({self.error_message})"


# Utility Functions

def try_call(func, *args, **kwargs):
	"""
	Tries to call the function and returns a ValidResult or ErrorResult.
	Captures exceptions and stack traces in case of errors.
	"""
	try:
		return ValidResult(func(*args, **kwargs))
	except Exception as e:
		return ErrorResult.from_exception(e)


# Example Usage
if __name__ == "__main__":
	def main():
		# Example 1: Basic Chaining with then()
		def increment(x):
			return ValidResult(x + 1)

		def double(x):
			return ValidResult(x * 2)

		def to_string(x):
			return ValidResult(f"The result is {x}")

		result = ValidResult(5)
		final_result = result.then(increment).then(double).then(to_string)

		if isinstance(final_result, ValidResult):
			print(final_result.get_result())  # Output: "The result is 12"
		else:
			final_result.dump()

		# Example 2: Handling Errors
		def safe_divide(x):
			if x == 0:
				return ErrorResult("Division by zero")
			else:
				return ValidResult(10 / x)

		def multiply_by_three(x):
			return ValidResult(x * 3)

		def multiply_by(n):
			def _core(x):
				return ValidResult(n * 3)

			return _core

		result = ValidResult(0)
		final_result = result.then(safe_divide).then(multiply_by_three)

		if isinstance(final_result, ValidResult):
			print(final_result.get_result())
		else:
			final_result.dump()

		# Example 3: Capturing Exceptions and Stack Traces
		def faulty_function(x):
			return 10 / x  # Will raise ZeroDivisionError if x is 0

		result = try_call(faulty_function, 0)

		if isinstance(result, ValidResult):
			print(f"Success: {result.get_result()}")
		else:
			result.dump()


	main()
