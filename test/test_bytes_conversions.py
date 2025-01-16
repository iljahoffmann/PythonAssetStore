import unittest
from lib.bytes_conversions import encode_to_base64, decode_from_base64


class TestBase64Conversion(unittest.TestCase):

    def test_standard_mapping(self):
        data = b"Hello, World!"
        encoded = encode_to_base64(data, mapping='standard')
        decoded = decode_from_base64(encoded, mapping='standard')
        self.assertEqual(data, decoded)

    def test_urlsafe_mapping(self):
        data = b"Hello, URL-Safe Base64!"
        encoded = encode_to_base64(data, mapping='urlsafe')
        decoded = decode_from_base64(encoded, mapping='urlsafe')
        self.assertEqual(data, decoded)

    def test_imap_mapping(self):
        data = b"Hello, IMAP Base64!"
        encoded = encode_to_base64(data, mapping='imap')
        decoded = decode_from_base64(encoded, mapping='imap')
        self.assertEqual(data, decoded)

    def test_bytearray_input(self):
        data = bytearray(b"Bytearray Test")
        encoded = encode_to_base64(data, mapping='standard')
        decoded = decode_from_base64(encoded, mapping='standard')
        self.assertEqual(data, bytearray(decoded))

    def test_invalid_mapping(self):
        data = b"Invalid Mapping Test"
        with self.assertRaises(ValueError):
            encode_to_base64(data, mapping='invalid')
        with self.assertRaises(ValueError):
            decode_from_base64(data, mapping='invalid')

    def test_type_error(self):
        with self.assertRaises(TypeError):
            encode_to_base64("string input", mapping='standard')
        with self.assertRaises(TypeError):
            decode_from_base64("string input", mapping='standard')

if __name__ == "__main__":
    unittest.main()
