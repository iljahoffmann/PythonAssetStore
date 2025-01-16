import base64

# Supported string encodings
string_encodings = {
    'utf-8', 'utf-16', 'utf-32', 'utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be',
    'ascii', 'latin-1', 'iso-8859-2', 'iso-8859-3', 'cp1252', 'cp437',
    'big5', 'gb2312', 'shift_jis', 'euc-kr'
}

# Mapping name to (encoder, decoder) callable
MAPPINGS = {
    'standard': (base64.b64encode, base64.b64decode),
    'urlsafe': (base64.urlsafe_b64encode, base64.urlsafe_b64decode),
    'imap': (
        lambda data: base64.b64encode(data).replace(b'/', b','),
        lambda data: base64.b64decode(data.replace(b',', b'/'))
    )
}

def _base64_encode(data: bytes, mapping: str = 'standard') -> bytes:
    """
    Core helper to encode bytes to base64.

    Parameters:
        data (bytes): The byte sequence to encode.
        mapping (str): Encoding mapping ('standard', 'urlsafe', or 'imap').

    Returns:
        bytes: The Base64-encoded bytes.
    """
    if mapping in MAPPINGS:
        encoder, _ = MAPPINGS[mapping]
        return encoder(data)
    else:
        raise ValueError("Unsupported mapping. Choose 'standard', 'urlsafe', or 'imap'.")

def _base64_decode(data: bytes, mapping: str = 'standard') -> bytes:
    """
    Core helper to decode Base64 bytes to original bytes.

    Parameters:
        data (bytes): The Base64-encoded byte sequence to decode.
        mapping (str): Encoding mapping ('standard', 'urlsafe', or 'imap').

    Returns:
        bytes: The decoded byte sequence.
    """
    if mapping in MAPPINGS:
        _, decoder = MAPPINGS[mapping]
        return decoder(data)
    else:
        raise ValueError("Unsupported mapping. Choose 'standard', 'urlsafe', or 'imap'.")

def encode_to_base64(data, mapping='standard'):
    """
    Encodes bytes or bytearray to Base64.

    Parameters:
        data (bytes | bytearray): The input data to encode.
        mapping (str): Encoding mapping ('standard', 'urlsafe', or 'imap').

    Returns:
        The Base64-encoded data in the same type as input (bytes or bytearray).
    """
    if isinstance(data, (bytes, bytearray)):
        encoded = _base64_encode(bytes(data), mapping)
        return encoded if isinstance(data, bytes) else bytearray(encoded)
    else:
        raise TypeError("Input must be of type 'bytes' or 'bytearray'.")

def decode_from_base64(data, mapping='standard'):
    """
    Decodes Base64 bytes or bytearray to original data.

    Parameters:
        data (bytes | bytearray): The Base64-encoded input data to decode.
        mapping (str): Encoding mapping ('standard', 'urlsafe', or 'imap').

    Returns:
        The decoded data in the same type as input (bytes or bytearray).
    """
    if isinstance(data, (bytes, bytearray)):
        decoded = _base64_decode(bytes(data), mapping)
        return decoded if isinstance(data, bytes) else bytearray(decoded)
    else:
        raise TypeError("Input must be of type 'bytes' or 'bytearray'.")

def str_to_bytes(string: str, encoding: str = 'utf-8') -> bytes:
    """
    Converts a string to bytes using the specified encoding.

    Parameters:
        string (str): The string to convert.
        encoding (str): The encoding to use (default is 'utf-8').

    Returns:
        bytes: The encoded bytes.
    """
    return string.encode(encoding)

def bytes_to_str(data: bytes, encoding: str = 'utf-8') -> str:
    """
    Converts bytes to a string using the specified encoding.

    Parameters:
        data (bytes): The byte sequence to convert.
        encoding (str): The encoding to use (default is 'utf-8').

    Returns:
        str: The decoded string.
    """
    return data.decode(encoding)

def str_to_bytearray(string: str, encoding: str = 'utf-8') -> bytearray:
    """
    Converts a string to a bytearray using the specified encoding.

    Parameters:
        string (str): The string to convert.
        encoding (str): The encoding to use (default is 'utf-8').

    Returns:
        bytearray: The encoded bytearray.
    """
    return bytearray(string.encode(encoding))

def bytearray_to_str(data: bytearray, encoding: str = 'utf-8') -> str:
    """
    Converts a bytearray to a string using the specified encoding.

    Parameters:
        data (bytearray): The bytearray to convert.
        encoding (str): The encoding to use (default is 'utf-8').

    Returns:
        str: The decoded string.
    """
    return data.decode(encoding)

# Example usage
if __name__ == "__main__":
    # Input data
    data_bytes = b"Hello, Base64!"
    data_bytearray = bytearray(data_bytes)

    # Encode to Base64
    encoded_bytes = encode_to_base64(data_bytes, mapping='imap')
    encoded_bytearray = encode_to_base64(data_bytearray, mapping='imap')
    print("Encoded (bytes):", encoded_bytes)
    print("Encoded (bytearray):", encoded_bytearray)

    # Decode from Base64
    decoded_bytes = decode_from_base64(encoded_bytes, mapping='imap')
    decoded_bytearray = decode_from_base64(encoded_bytearray, mapping='imap')
    print("Decoded (bytes):", decoded_bytes)
    print("Decoded (bytearray):", decoded_bytearray)

    # String to bytes and bytearray
    test_string = "Hello, Conversion!"
    print("String to bytes:", str_to_bytes(test_string))
    print("Bytes to string:", bytes_to_str(data_bytes))
    print("String to bytearray:", str_to_bytearray(test_string))
    print("Bytearray to string:", bytearray_to_str(data_bytearray))
