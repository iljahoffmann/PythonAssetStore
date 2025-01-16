def set_bit(number: int, bit_index: int) -> int:
	"""
	Sets the bit at the given index to 1.
	"""
	return number | (1 << bit_index)

def clear_bit(number: int, bit_index: int) -> int:
	"""
	Clears the bit at the given index (sets it to 0).
	"""
	return number & ~(1 << bit_index)

def test_bit(number: int, bit_index: int) -> bool:
	"""
	Tests if the bit at the given index is set (1).
	"""
	return (number & (1 << bit_index)) != 0

def set_bits(number: int, mask: int) -> int:
	"""
	Sets bits specified by the mask to 1.
	"""
	return number | mask

def clear_bits(number: int, mask: int) -> int:
	"""
	Clears bits specified by the mask (sets them to 0).
	"""
	return number & ~mask

def test_bits(number: int, mask: int) -> bool:
	"""
	Tests if all bits specified by the mask are set (1).
	"""
	return (number & mask) == mask

def as_binary_string(i: int, bits: int=32):
	"""
	Convert a natural number into a string representing its value as bit-string.

	Args:
		i (int): the number to convert.
		bits (int): the assumed len of an integer in bits (since python ints can have arbitrary length).
	"""
	return format(i & (2 ** bits - 1), f'0{bits}b')
