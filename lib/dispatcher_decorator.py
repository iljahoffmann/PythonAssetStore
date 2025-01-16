import traceback

from lib.precondition import *


class DispatchedNamespace:
    def __init__(self, debug=False):
        self._variants = {}
        self._debug = debug

    def variant(self, method):
        """
        A <<decorator>> that allows for method overloading by function signature.

        This decorator is designed to optionally be used in tandem with the precondition decorator.
        If it is, this decorator must be the outer decorator and the precondition must be the inner one.

        Dispatched methods are identified by [class.]name and matched against the parameters of
        the current invocation:
        - if the dispatched method is not decorated by a precondition, the number of arguments in the
        prototype of the function must match the number of arguments provided to the call
        - if it has a precondition, then that precondition must be satisfied

        The methods are processed in the same order as implemented in the class or module and
        the result of the call to the first matching function is returned.

        Raises TypeError, if no matching function was found.
        """
        if has_precondition(method):
            real_method = guarded_function(method)
            method_name = real_method.__name__
            cls_name = real_method.__qualname__.rsplit('.', maxsplit=1)[0]
        else:
            method_name = method.__name__
            # Extract class name from method's qualified name
            cls_name = method.__qualname__.rsplit('.', maxsplit=1)[0]

        if cls_name not in self._variants:
            self._variants[cls_name] = {}

        if method_name not in self._variants[cls_name]:
            self._variants[cls_name][method_name] = []

        self._variants[cls_name][method_name].append(
            (method, function_signature(method)))

        def dispatcher(*args, **kwargs):
            # print(f"Called {cls_name}.{method_name} with args: {args}, kwargs: {kwargs}")

            # Dispatch to the correct method variant based on the number of arguments or matching precondition.
            # Since this is a prepared call, all keys in _variants are (or rather: should be) guaranteed to exist.
            for method_variant, signature in self._variants[cls_name][method_name]:
                if has_precondition(method_variant):
                    if precondition_ok(method_variant, *args, **kwargs):
                        try:
                            result = unconditional_call(method_variant, *args, **kwargs)
                        except Exception as ex:
                            traceback.print_exc()
                            raise
                        return result
                elif len(args) == len(signature.parameters):
                    return method_variant(*args, **kwargs)
            raise TypeError(
                f"No variant of method {cls_name}.{method_name} found for arguments {args}/{kwargs}")

        return dispatcher

    def conditional(self, **kwargs):
        """
        Helper <<decorator>> to apply 'variant' and 'precondition' in one step.
        """
        def _real_decorator(func):
            if self._debug:
                kwargs.update({'debug': self._debug})
            try:
                return self.variant(precondition(**kwargs)(func))
            except Exception as ex:
                print(ex)
                traceback.print_tb()
                raise

        return _real_decorator


if __name__ == '__main__':
    from lib.precondition import *
    from lib.value_predicate import *

    def main():
        example_class = DispatchedNamespace(debug=False)

        class ExampleClass:
            # @example_class.variant
            # @precondition(
            @example_class.conditional(
                arg1=is_in(['arg1', 'arg2'])
            )
            def example_method(self, arg1: str):
                return f"Method with one string argument: {arg1}"

            @example_class.variant
            def example_method(self, arg1, arg2):
                return f"Method with two arguments: {arg1}, {arg2}"

            @example_class.conditional()
            def other_method(self, arg1: str, arg2):
                return f"Other method with two arguments: {arg1}, {arg2}, and the first one is a string"

            @example_class.conditional(
                arg1=in_range(0, 3)
            )
            def other_method(self, arg1: int, arg2):
                return f"Other method with two arguments: {arg1}, {arg2}, and the first one is an integer"

        # Create an instance of ExampleClass
        example_instance = ExampleClass()

        # Test the method variants
        test_output_one_arg = example_instance.example_method("arg2")
        test_output_two_args = example_instance.example_method("arg1", "arg2")
        other_test_output_two_args = example_instance.other_method(3, "arg2")

        print(test_output_one_arg, test_output_two_args,
              other_test_output_two_args)

        pass

    main()
    pass
