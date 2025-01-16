import os
import unittest
import tempfile
from lib.module_loader import load_or_update_module


class TestLoadOrUpdateModule(unittest.TestCase):
    def setUp(self):
        # Create a temporary Python module file
        self.temp_module_path = os.path.join(tempfile.gettempdir(), "test_temp_module.py")
        with open(self.temp_module_path, 'w') as f:
            f.write("def test_function():\n    return 'Hello, World!'\n")
        self.module_path = self.temp_module_path

    def tearDown(self):
        # Clean up the temporary module file
        os.remove(self.module_path)

    def test_load_module(self):
        # Test loading the module for the first time
        module = load_or_update_module(self.module_path)
        self.assertTrue(hasattr(module, 'test_function'))
        self.assertEqual(module.test_function(), 'Hello, World!')

    def test_reload_from_module(self):
        # Test reloading the module after modification
        module = load_or_update_module(self.module_path)
        self.assertTrue(hasattr(module, 'test_function'))
        self.assertEqual(module.test_function(), 'Hello, World!')

        # Modify the module content
        with open(self.module_path, 'w') as f:
            f.write("def test_function():\n    return 'Hello, Universe!'\n")

        # Reload the module and test the updated function
        updated_module = load_or_update_module(module)
        self.assertTrue(hasattr(updated_module, 'test_function'))
        self.assertEqual(updated_module.test_function(), 'Hello, Universe!')

    def test_reload_from_file(self):
        # Test reloading the module after modification
        module = load_or_update_module(self.module_path)
        self.assertTrue(hasattr(module, 'test_function'))
        self.assertEqual(module.test_function(), 'Hello, World!')

        # Modify the module content
        with open(self.module_path, 'w') as f:
            f.write("def test_function():\n    return 'Bye then'\n")

        # Reload the module by filename and test the updated function
        updated_module = load_or_update_module(self.module_path)
        self.assertTrue(hasattr(updated_module, 'test_function'))
        updated_result = updated_module.test_function()
        self.assertEqual(updated_result, 'Bye then')

    def test_invalid_path_should_raise(self):
        self.assertRaises(FileNotFoundError, load_or_update_module, "./no_such_file_or_directory.py")


if __name__ == "__main__":
    unittest.main()
