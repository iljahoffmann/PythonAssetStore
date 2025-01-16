import unittest
from lib.shared_dict import SharedDict


class TestSharedDict(unittest.TestCase):
	def setUp(self):
		"""
		Create a fresh shared dictionary and a SharedDict for each test.
		"""
		self.shared_storage = {}
		self.sd = SharedDict(self.shared_storage)

	def test_set_and_get(self):
		# Test setting and getting items
		self.sd['a'] = 1
		self.assertEqual(self.sd['a'], 1)
		self.assertEqual(self.shared_storage['a'], 1)

		# Test that KeyError is raised for a non-existent key
		with self.assertRaises(KeyError):
			_ = self.sd['b']

	def test_contains(self):
		self.sd['x'] = 42
		self.assertIn('x', self.sd)
		self.assertNotIn('z', self.sd)

	def test_deletion(self):
		self.sd['key'] = 'value'
		del self.sd['key']
		self.assertNotIn('key', self.sd)
		self.assertNotIn('key', self.shared_storage)

		# Deleting a non-existent key should raise KeyError
		with self.assertRaises(KeyError):
			del self.sd['non_existent']

	def test_update(self):
		self.sd.update({'k1': 10, 'k2': 20})
		self.assertEqual(self.sd['k1'], 10)
		self.assertEqual(self.sd['k2'], 20)
		self.assertEqual(self.shared_storage, {'k1': 10, 'k2': 20})

		# Updating via kwargs
		self.sd.update(k3=30, k4=40)
		self.assertEqual(self.sd['k3'], 30)
		self.assertEqual(self.sd['k4'], 40)
		self.assertEqual(self.shared_storage, {'k1': 10, 'k2': 20, 'k3': 30, 'k4': 40})

	def test_keys_values_items(self):
		self.sd.update({'x': 1, 'y': 2, 'z': 3})
		self.assertEqual(set(self.sd.keys()), {'x', 'y', 'z'})
		self.assertEqual(set(self.sd.values()), {1, 2, 3})
		self.assertEqual(set(self.sd.items()), {('x', 1), ('y', 2), ('z', 3)})

	def test_len_and_iter(self):
		self.sd.update({'x': 1, 'y': 2, 'z': 3})
		self.assertEqual(len(self.sd), 3)

		# Test iteration
		keys = [key for key in self.sd]
		self.assertEqual(set(keys), {'x', 'y', 'z'})

	def test_pop(self):
		self.sd['a'] = 100
		popped_value = self.sd.pop('a')
		self.assertEqual(popped_value, 100)
		self.assertNotIn('a', self.sd)

		# Test pop with default
		default_value = self.sd.pop('non_existent', 'default')
		self.assertEqual(default_value, 'default')

	def test_popitem(self):
		self.sd.update({'p1': 10, 'p2': 20})
		popped_key, popped_value = self.sd.popitem()
		self.assertNotIn(popped_key, self.sd)
		self.assertNotIn(popped_key, self.shared_storage)
		self.assertIn('p1', self.sd)  # The other key should still be there

	def test_clear(self):
		self.sd.update({'x': 1, 'y': 2})
		self.sd.clear()
		self.assertEqual(len(self.sd), 0)
		self.assertEqual(len(self.shared_storage), 0)

	def test_copy(self):
		self.sd.update({'copykey1': 'alpha', 'copykey2': 'beta'})
		sd_copy = self.sd.copy()  # This should return a *copy* of the shared dict
		self.assertEqual(sd_copy, {'copykey1': 'alpha', 'copykey2': 'beta'})
		# Ensure it's truly a separate dictionary (changes in original reflect in `_shared` but not in `sd_copy`)
		self.sd['copykey1'] = 'modified'
		self.assertEqual(self.sd['copykey1'], 'modified')
		self.assertNotEqual(sd_copy['copykey1'], 'modified')

	def test_setdefault(self):
		val = self.sd.setdefault('k', 999)
		self.assertEqual(val, 999)
		self.assertEqual(self.sd['k'], 999)
		self.assertEqual(self.shared_storage['k'], 999)

	def test_repr(self):
		self.sd.update({'r': 1})
		rep = repr(self.sd)
		self.assertIn('SharedDict', rep)
		self.assertIn("'r': 1", rep)

	def test_shared_behavior_across_instances(self):
		"""
		Ensures that multiple SharedDict instances pointing to the same
		underlying dict really do reflect changes to each other.
		"""
		sd2 = SharedDict(self.shared_storage)
		self.sd['shared'] = 'yes'
		self.assertEqual(sd2['shared'], 'yes')

		sd2['another_key'] = 'another_value'
		self.assertEqual(self.sd['another_key'], 'another_value')


if __name__ == '__main__':
	unittest.main()
