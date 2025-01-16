import io
import unittest
from lib.call_result import ValidResult, ErrorResult, try_call


class TestCallResult(unittest.TestCase):

    def test_valid_result_chain(self):
        def increment(x):
            return ValidResult(x + 1)

        def double(x):
            return ValidResult(x * 2)

        result = ValidResult(5)
        final_result = result.then(increment).then(double)

        self.assertIsInstance(final_result, ValidResult)
        self.assertEqual(final_result.get_result(), 12)

    def test_error_result_propagation(self):
        def safe_divide(x):
            if x == 0:
                return ErrorResult("Division by zero")
            return ValidResult(10 / x)

        result = ValidResult(0).then(safe_divide)

        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.get_error_message(), "Division by zero")

    def test_error_handling_in_then(self):
        def faulty_function(x):
            raise ValueError("Something went wrong")

        result = ValidResult(5).then(faulty_function)

        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.get_error_message(), "Something went wrong")

    def test_try_call_success(self):
        def successful_function(x):
            return x + 10

        result = try_call(successful_function, 5)

        self.assertIsInstance(result, ValidResult)
        self.assertEqual(result.get_result(), 15)

    def test_try_call_exception(self):
        def failing_function(x):
            raise RuntimeError("Unexpected error")

        result = try_call(failing_function, 5)

        self.assertIsInstance(result, ErrorResult)
        self.assertIn("Unexpected error", result.get_error_message())

    def test_nested_valid_results(self):
        nested = ValidResult(ValidResult(10))
        self.assertEqual(nested.get_result(), 10)

    def test_valid_result_dump(self):
        result = ValidResult(42)
        stream = io.StringIO()
        result.dump(stream=stream)
        log = stream.getvalue()
        self.assertIn("ValidResult(42)", log)

    def test_error_result_dump(self):
        result = ErrorResult("Test error")
        stream = io.StringIO()
        result.dump(stream=stream)
        log = stream.getvalue()
        self.assertIn("Error: Test error", log)


if __name__ == "__main__":
    unittest.main()
