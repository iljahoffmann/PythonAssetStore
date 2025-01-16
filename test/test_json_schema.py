import unittest
from lib.json_schema import Object, Array, Type, Value, Custom, validate_structure, Optional


class TestSchemaValidation(unittest.TestCase):
    def test_valid_structure(self):
        schema = Object({
            "name": Type(str),
            "age": Type(int),
            "tags": Array(all=Type(str)),
            "coordinates": Array(items=[Type(int), Type(int), Type(int)]),
            "metadata": Object({
                "id": Type(int),
                "valid": Custom(lambda x: isinstance(x, bool) and x is True)
            }),
            "status": Value("active")
        })

        structure = {
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
        self.assertTrue(validate_structure(schema, structure))

    def test_missing_key(self):
        schema = Object({
            "name": Type(str),
            "age": Type(int)
        })

        structure = {
            "name": "Alice"
        }
        self.assertFalse(validate_structure(schema, structure))

    def test_missing_optional_key(self):
        schema = Object({
            "name": Type(str),
            "age": Optional(Type(int))
        })

        structure = {
            "name": "Alice"
        }
        self.assertTrue(validate_structure(schema, structure))

    def test_type_mismatch(self):
        schema = Object({
            "name": Type(str),
            "age": Type(int)
        })

        structure = {
            "name": "Alice",
            "age": "30"
        }
        self.assertFalse(validate_structure(schema, structure))

    def test_type_mismatch_on_optional(self):
        schema = Object({
            "name": Type(str),
            "age": Optional(Type(int))
        })

        structure = {
            "name": "Alice",
            "age": "30"
        }
        self.assertFalse(validate_structure(schema, structure))

    def test_key_validator(self):
        schema = Object(
            keys=Type(str)
        )

        structure = {
            "name": "Alice",
            "age": 30
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "name": "Alice",
            "age": 30,
            17: 4
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

    def test_value_validator(self):
        schema = Object(
            values=Type(str)
        )

        structure = {
            "name": "Alice",
            "status": "active",
            800: "yes"
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "name": "Alice",
            "status": "active",
            "age": 30,
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

    def test_array_all_elements(self):
        schema = Object({
            "tags": Array(all=Type(str))
        })

        structure = {
            "tags": ["python", "developer"]
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "tags": ["python", 123]
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

    def test_array_specific_items(self):
        schema = Object({
            "coordinates": Array(items=[Type(int), Type(int), Type(int)])
        })

        structure = {
            "coordinates": [10, 20, 30]
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "coordinates": [10, 20]
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

    def test_array_specific_items_failures(self):
        # Schema expects an array with three integers in specific order
        schema = Object({
            "coordinates": Array(items=[Type(int), Type(int), Type(int)])
        })

        # Case 1: Type mismatch for a specific item
        structure_type_mismatch = {
            "coordinates": [10, "20", 30]  # Second item is a string, not an int
        }
        self.assertFalse(validate_structure(schema, structure_type_mismatch))

        # Case 2: Incomplete array
        structure_incomplete = {
            "coordinates": [10, 20]  # Missing the third item
        }
        self.assertFalse(validate_structure(schema, structure_incomplete))

        # Case 3: Extra elements in the array
        structure_extra_items = {
            "coordinates": [10, 20, 30, 40]  # Fourth item is not expected
        }
        self.assertFalse(validate_structure(schema, structure_extra_items))

    def test_value_equality(self):
        schema = Object({
            "status": Value("active")
        })

        structure = {
            "status": "active"
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "status": "inactive"
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

    def test_custom_validation(self):
        schema = Object({
            "flag": Custom(lambda x: isinstance(x, int) and x > 0)
        })

        structure = {
            "flag": 10
        }
        self.assertTrue(validate_structure(schema, structure))

        structure_invalid = {
            "flag": -5
        }
        self.assertFalse(validate_structure(schema, structure_invalid))

if __name__ == "__main__":
    unittest.main()
