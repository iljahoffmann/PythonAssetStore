from lib.layered_dict import LayeredDict
import unittest


class TestLayeredDict(unittest.TestCase):
    def setUp(self):
        self.layer1 = {"a": 1, "b": 2}
        self.layer2 = {"b": 3, "c": 4, "e": 10}  # Adding "e" specific to layer2
        self.current = {"c": 5, "d": 6}
        self.ld = LayeredDict(current=self.current, layers=[self.layer1, self.layer2])

    def test_getitem(self):
        self.assertEqual(self.ld["a"], 1)  # From layer1
        self.assertEqual(self.ld["b"], 2)  # From layer1 (overrides layer2)
        self.assertEqual(self.ld["c"], 5)  # From current
        self.assertEqual(self.ld["d"], 6)  # From current
        self.assertEqual(self.ld["e"], 10)  # From layer2
        with self.assertRaises(KeyError):
            _ = self.ld["nonexistent"]

    def test_setitem(self):
        self.ld["f"] = 7
        self.assertEqual(self.ld["f"], 7)
        self.assertEqual(self.current["f"], 7)

    def test_delitem(self):
        del self.ld["d"]
        self.assertNotIn("d", self.ld)
        with self.assertRaises(PermissionError):
            del self.ld["b"]  # Exists only in layers

    def test_contains(self):
        self.assertIn("a", self.ld)
        self.assertIn("b", self.ld)
        self.assertIn("c", self.ld)
        self.assertIn("e", self.ld)  # Specific to layer2
        self.assertNotIn("nonexistent", self.ld)

    def test_len(self):
        self.assertEqual(len(self.ld), 5)  # Includes "e"

    def test_add_layer(self):
        new_layer = {"f": 8}
        self.ld.add_layer(new_layer)
        self.assertIn("f", self.ld)
        self.assertEqual(self.ld["f"], 8)

    def test_insert_layer(self):
        new_layer = {"z": 9}
        self.ld.insert_layer(0, new_layer)
        self.assertIn("z", self.ld)
        self.assertEqual(self.ld["z"], 9)

    def test_remove_layer(self):
        self.ld.remove_layer(self.layer1)
        self.assertNotIn("a", self.ld)
        self.assertIn("b", self.ld)  # From layer2
        with self.assertRaises(ValueError):
            self.ld.remove_layer({"nonexistent": 10})

    def test_enumerate_layers(self):
        layers = self.ld.enumerate_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0][1], self.layer1)
        self.assertEqual(layers[1][1], self.layer2)

    def test_nested_layers_depth_1(self):
        nested_layer = LayeredDict(current={"nested_key": 100}, layers=[{"nested_layer_key": 200}])
        self.ld.add_layer(nested_layer)
        self.assertIn("nested_key", self.ld)
        self.assertIn("nested_layer_key", self.ld)
        self.assertEqual(self.ld["nested_key"], 100)
        self.assertEqual(self.ld["nested_layer_key"], 200)

    def test_nested_layers_depth_2(self):
        inner_nested_layer = LayeredDict(current={"inner_key": 300}, layers=[{"inner_layer_key": 400}])
        nested_layer = LayeredDict(current={"nested_key": 100}, layers=[{"nested_layer_key": 200}, inner_nested_layer])
        self.ld.add_layer(nested_layer)

        # Check keys in the second nested layer
        self.assertIn("nested_key", self.ld)
        self.assertIn("nested_layer_key", self.ld)
        self.assertIn("inner_key", self.ld)
        self.assertIn("inner_layer_key", self.ld)

        self.assertEqual(self.ld["nested_key"], 100)
        self.assertEqual(self.ld["nested_layer_key"], 200)
        self.assertEqual(self.ld["inner_key"], 300)
        self.assertEqual(self.ld["inner_layer_key"], 400)

    def test_nested_layers_depth_3(self):
        inner_inner_nested_layer = LayeredDict(current={"deep_key": 500}, layers=[{"deep_layer_key": 600}])
        inner_nested_layer = LayeredDict(current={"inner_key": 300}, layers=[{"inner_layer_key": 400}, inner_inner_nested_layer])
        nested_layer = LayeredDict(current={"nested_key": 100}, layers=[{"nested_layer_key": 200}, inner_nested_layer])
        self.ld.add_layer(nested_layer)

        # Check keys in the third nested layer
        self.assertIn("nested_key", self.ld)
        self.assertIn("nested_layer_key", self.ld)
        self.assertIn("inner_key", self.ld)
        self.assertIn("inner_layer_key", self.ld)
        self.assertIn("deep_key", self.ld)
        self.assertIn("deep_layer_key", self.ld)

        self.assertEqual(self.ld["nested_key"], 100)
        self.assertEqual(self.ld["nested_layer_key"], 200)
        self.assertEqual(self.ld["inner_key"], 300)
        self.assertEqual(self.ld["inner_layer_key"], 400)
        self.assertEqual(self.ld["deep_key"], 500)
        self.assertEqual(self.ld["deep_layer_key"], 600)


if __name__ == "__main__":
    unittest.main()
