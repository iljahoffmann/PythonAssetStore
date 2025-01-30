import inspect
import traceback

from lib.value_predicate import is_a, predicate_matches, is_optional_predicate


class PreconditionFailed(Exception):
    def __init__(self, function, parameter_name, predicate, value):
        self.function = function
        self.parameter = parameter_name
        self.predicate = predicate
        self.value = value


"""
	Decorator that checks preconditions before executing a function.

	Args:
		debug (bool, optional): Flag to enable debug mode. Defaults to False.
		**precondition_kwargs: Keyword arguments representing the preconditions.

	Returns:
		The decorated function.

	Raises:
		PreconditionFailed: If any of the preconditions are not met.

	Example:
		@precondition(debug=True, this=lambda x: isinstance(x, MyClass), param1=lambda x: x > 0)
		def my_function(this: MyClass, param1: int, param2: str):
			# Function implementation

		The above example decorates the `my_function` with preconditions. The `debug` flag is set to True,
		which means that if any precondition fails, a debug message will be printed. The preconditions are
		defined using keyword arguments, where the key represents the parameter name and the value is a
		predicate function that checks the condition. In this example, the `this` parameter must be an
		instance of `MyClass` and the `param1` parameter must be greater than 0. If any of these preconditions
		are not met, a `PreconditionFailed` exception will be raised.
"""


def precondition(debug=False, **precondition_kwargs):
    def _wrapper(function):
        def _check_preconditions(*call_args, **call_kwargs):
            def _next_signature_parameter():
                try:
                    return next(signature_parameters)
                except StopIteration:
                    raise PreconditionFailed(
                        function, parameter_name, 'missing', None)

            def _raise_error(_f, _p, _r, _v):
                try:
                    _m = _r.__str__()
                except TypeError:
                    _m = str(_r)
                error = PreconditionFailed(_f, _p, _m, _v)
                if debug:
                    if callable(debug):
                        debug(error)
                    else:
                        print('PreconditionFailed', str(error))
                raise error

            nonlocal precondition_kwargs, method_signature

            to_check = dict(precondition_kwargs)
            signature_parameters = iter(method_signature.parameters.items())

            # process positional arguments
            for parameter_value in call_args:
                parameter_name, parameter_declaration = _next_signature_parameter()
                # check type annotation
                if parameter_declaration.annotation != inspect.Parameter.empty:
                    if not is_a(parameter_declaration.annotation)(parameter_value):
                        _raise_error(function, parameter_name, parameter_declaration.annotation, parameter_value)
                # check precondition
                if parameter_name in precondition_kwargs:
                    if parameter_name == 'this':
                        if not predicate_matches(precondition_kwargs[parameter_name], function.__self__):
                            _raise_error(
                                function, parameter_name, precondition_kwargs[parameter_name], function.__self__)
                    elif not predicate_matches(precondition_kwargs[parameter_name], parameter_value):
                        _raise_error(
                            function, parameter_name, precondition_kwargs[parameter_name], parameter_value)
                    del to_check[parameter_name]

            # process keyword arguments
            unprocessed_call_parameters = {k: v for k, v in signature_parameters}
            has_kwargs = len([v for v in unprocessed_call_parameters.values() if v.kind == v.VAR_KEYWORD]) > 0

            for parameter_call_name in call_kwargs:
                if parameter_call_name not in unprocessed_call_parameters:
                    if has_kwargs or (
                        precondition_entry := precondition_kwargs.get(parameter_call_name) and
                        is_optional_predicate(precondition_entry)
                    ):
                        continue
                    _raise_error(function, parameter_name, parameter_declaration.annotation, parameter_value)

                osp_pcn = unprocessed_call_parameters[parameter_call_name]
                parameter_declaration = osp_pcn if isinstance(osp_pcn, inspect.Parameter) else osp_pcn[1]
                parameter_value = call_kwargs[parameter_call_name]

                # check type annotation
                if parameter_declaration.annotation != inspect.Parameter.empty:
                    if not is_a(parameter_declaration.annotation)(parameter_value):
                        _raise_error(function, parameter_name, parameter_declaration.annotation, parameter_value)

                predicate = precondition_kwargs.get(parameter_call_name, inspect.Parameter.empty)
                if predicate != inspect.Parameter.empty:
                    parameter_value = call_kwargs[parameter_call_name]
                    if not predicate_matches(predicate, parameter_value):
                        _raise_error(function, parameter_call_name, predicate, parameter_value)

                if parameter_call_name in to_check:
                    del to_check[parameter_call_name]

                del unprocessed_call_parameters[parameter_call_name]

            if len(unprocessed_call_parameters) > 0:
                missing_parameter = {
                    k: v for k, v in
                    unprocessed_call_parameters.items()
                    if v.default == inspect.Parameter.empty
                }
                if len(missing_parameter) > 0:
                    for kw in missing_parameter:
                        if kw in precondition_kwargs and is_optional_predicate(precondition_kwargs[kw]):
                            continue
                        p = missing_parameter[kw]
                        if p.kind == p.VAR_KEYWORD:
                            continue
                        _raise_error(function, parameter_name, f'missing {unprocessed_call_parameters}', None)

            # finally, check un-processed signature entries
            for parameter_name, parameter_declaration in to_check.items():
                predicate = parameter_declaration if callable(parameter_declaration) else parameter_declaration.default
                if not is_optional_predicate(predicate):
                    _raise_error(function, parameter_name, 'checked but missing', None)

        def _caller(*call_args, **call_kwargs):
            return function(*call_args, **call_kwargs)

        def _make_call(*call_args, **call_kwargs):
            _check_preconditions(*call_args, **call_kwargs)
            return _caller(*call_args, **call_kwargs)

        method_signature = inspect.signature(function)
        setattr(_make_call, '_signature', method_signature)
        setattr(_make_call, '_precondition', _check_preconditions)
        setattr(_make_call, '_unconditional_call', _caller)
        setattr(_make_call, '_preconditioned_function', function)
        setattr(_make_call, '__doc__', function.__doc__)
        return _make_call

    return _wrapper


def function_signature(a_callable):
    try:
        stored_signature = getattr(a_callable, '_signature')
        return stored_signature
    except AttributeError:
        return inspect.signature(a_callable)


def has_precondition(a_callable):
    """
    Primary test to check for a precondition decorator.
    If this function returns True, guarded_function(same_callable) should return the function instance for which
    the precondition is defined.
    """
    return hasattr(a_callable, '_precondition')


def guarded_function(a_callable):
    """
    Returns the function that is guarded by the callable or None, if the callable has no precondition
    """
    try:
        return getattr(a_callable, '_preconditioned_function')
    except AttributeError:
        return None


def precondition_ok(a_callable, *args, **kwargs):
    """
    Raises PreconditionFailed if the callable has a precondition that is not fulfilled
    """
    try:
        pre = getattr(a_callable, '_precondition')
        pre(*args, **kwargs)
        return True
    except (AttributeError, PreconditionFailed):
        return False


def unconditional_call(a_callable, *args, **kwargs):
    """
    Perform a
    - normal function call on callables that have no precondition
    - an unverified call with no precondition check, if the callable has (or rather 'is') a precondition
    """
    try:
        call = getattr(a_callable, '_unconditional_call')
        return call(*args, **kwargs)
    except AttributeError:
        return a_callable(*args, **kwargs)
    except Exception:
        raise


if __name__ == '__main__':
    def main():
        from lib.value_predicate import in_range

        @precondition(a=in_range(1, 4))
        def foo(a: int, b=2):
            return 2*a+b

        checked = has_precondition(foo)
        x = foo(5)
        pass

    main()