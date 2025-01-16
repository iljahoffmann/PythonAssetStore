import unittest
from lib.path_op import *


class TestPathFunctions(unittest.TestCase):

    def test_simple_dict_set_get(self):
        data = {}
        path_set(data, "a.b.c", 42)
        self.assertEqual(path_get(data, "a.b.c"), 42)
        self.assertEqual(data, {"a": {"b": {"c": 42}}})

    def test_simple_list_set_get(self):
        data = {}
        path_set(data, "x[0]", 123)
        self.assertEqual(path_get(data, "x[0]"), 123)
        self.assertEqual(data, {"x": [123]})

        # Out of range index
        path_set(data, "x[2]", 999)
        self.assertEqual(path_get(data, "x[2]"), 999)
        self.assertEqual(data, {"x": [123, None, 999]})

    def test_list_of_dicts(self):
        data = {"members": [{"name": "Alice"}, {"name": "Bob"}]}
        self.assertEqual(path_get(data, "members[1].name"), "Bob")
        path_set(data, "members[0].age", 30)
        self.assertEqual(path_get(data, "members[0].age"), 30)

    def test_nested_lists(self):
        data = {}
        # Create a list of lists
        path_set(data, "arr[0][0]", "nested")
        self.assertEqual(data, {"arr": [["nested"]]})
        self.assertEqual(path_get(data, "arr[0][0]"), "nested")

        # Extend inner list
        path_set(data, "arr[0][2]", "hello")
        self.assertEqual(path_get(data, "arr[0][2]"), "hello")
        self.assertEqual(data, {"arr": [["nested", None, "hello"]]})

    def test_nested_dicts_and_lists(self):
        data = {}
        # a dict inside a list inside a dict
        path_set(data, "root.list[0].key", "value")
        self.assertEqual(path_get(data, "root.list[0].key"), "value")
        self.assertEqual(data, {"root": {"list": [{"key": "value"}]}})

    def test_get_non_existent(self):
        data = {"a": {"b": {"c": 42}}}
        self.assertIsNone(path_get(data, "a.b.x"))
        self.assertIsNone(path_get(data, "a.b.c.d"))
        self.assertIsNone(path_get(data, "x.y.z"))

        # Test with default
        self.assertEqual(path_get(data, "x.y.z", default="not found"), "not found")

    def test_delete_dict_key(self):
        data = {"a": {"b": {"c": 42}}}
        val = path_del(data, "a.b.c")
        self.assertEqual(val, 42)
        self.assertNotIn("c", data["a"]["b"])
        self.assertIsNone(path_del(data, "a.b.c"))

    def test_delete_dict_key_with_content(self):
        data = {"a": {"b": {"c": 42}}}
        val = path_del(data, "a.b")
        self.assertEqual(val, {"c": 42})
        self.assertNotIn("c", data["a"])
        self.assertIsNone(path_del(data, "a.b.c"))

    def test_delete_list_element(self):
        data = {"arr": [10, 20, 30]}
        val = path_del(data, "arr[1]")
        self.assertEqual(val, 20)
        self.assertEqual(data, {"arr": [10, 30]})
        self.assertIsNone(path_del(data, "arr[5]"))  # out-of-range

    def test_exception_default(self):
        data = {}
        exc = ValueError("Not found!")
        with self.assertRaises(ValueError):
            path_get(data, "nope", default=exc)

        with self.assertRaises(ValueError):
            path_del(data, "nope", default=exc)

    def test_treepath_reuse(self):
        data = {"a": {"b": {"c": 123}}}
        p = TreePath("a.b.c")
        # Using the same parsed path
        self.assertEqual(path_get(data, p), 123)

        path_set(data, p, 999)
        self.assertEqual(path_get(data, "a.b.c"), 999)

        val = path_del(data, p)
        self.assertEqual(val, 999)
        self.assertIsNone(path_get(data, p))

    def test_components_may_not_be_empty(self):
        with self.assertRaises(ValueError):
            x = TreePath('a..b')

    def test_path_iter(self):
        data = {"a": {"b": {"c": 42}}}
        p = TreePath("a.b.c")
        collected = [_ for _ in path_iter(data, p)]
        self.assertEqual(collected, [{"b": {"c": 42}}, {"c": 42}, 42])


if __name__ == '__main__':
    unittest.main()
