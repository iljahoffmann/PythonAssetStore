import unittest
from struct import unpack

from lib.store.user_registry import UserRegistry
from lib.store.unix_permissions import UnixPermissions, BasicPersistentObject


class TestUnixPermissions(unittest.TestCase):
	user_registry = UserRegistry()

	@classmethod
	def setUpClass(cls):
		# 3 users, 2 groups
		cls.user_registry.make_entity("alice")
		cls.user_registry.make_entity("bob")
		cls.user_registry.make_entity("charly")

		cls.user_registry.make_entity("team")
		cls.user_registry.make_entity("developers")

		# all team members are devs
		cls.user_registry.add_layer_to_entity("team", "developers")

		# bob is a member of the team
		cls.user_registry.add_layer_to_entity("bob", "team")
		pass

	def test_registry_persistence(self):
		packed_registry = self.user_registry.to_transport()
		unpacked_registry: UserRegistry = BasicPersistentObject.from_transport(packed_registry)
		self.assertTrue(unpacked_registry.get_entity('bob') is not None)

	def test_initialization_without_group(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice")

		# Check user keys
		self.assertTrue(perm.permissions["r:alice"])
		self.assertTrue(perm.permissions["w:alice"])
		self.assertTrue(perm.permissions["x:alice"])

		# Check that no group keys exist
		self.assertIsNone(perm.group_name)
		self.assertNotIn("r:developers", perm.permissions)

		# Check others
		self.assertTrue(perm.permissions["r:*"])
		self.assertTrue(perm.permissions["w:*"])
		self.assertTrue(perm.permissions["x:*"])

	def test_initialization_with_group(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")

		# Check user keys
		self.assertTrue(perm.permissions["r:alice"])
		self.assertTrue(perm.permissions["w:alice"])
		self.assertTrue(perm.permissions["x:alice"])

		# Check group keys
		self.assertTrue(perm.permissions["r:developers"])
		self.assertTrue(perm.permissions["w:developers"])
		self.assertTrue(perm.permissions["x:developers"])

		# Check others
		self.assertTrue(perm.permissions["r:*"])
		self.assertTrue(perm.permissions["w:*"])
		self.assertTrue(perm.permissions["x:*"])

	def test_chmod_with_octal_int(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")
		# chmod 755 -> user: rwx (7), group: r-x (5), others: r-x (5)
		perm.chmod(0o755)

		# User should have rwx
		self.assertTrue(perm.permissions["r:alice"])
		self.assertTrue(perm.permissions["w:alice"])
		self.assertTrue(perm.permissions["x:alice"])

		# Group should have r-x
		self.assertTrue(perm.permissions["r:developers"])
		self.assertFalse(perm.permissions["w:developers"])
		self.assertTrue(perm.permissions["x:developers"])

		# Others should have r-x
		self.assertTrue(perm.permissions["r:*"])
		self.assertFalse(perm.permissions["w:*"])
		self.assertTrue(perm.permissions["x:*"])

	def test_chmod_with_octal_string(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")
		# chmod '644' -> user: rw- (6), group: r-- (4), others: r-- (4)
		perm.chmod('644')

		# User: rw- (6 -> 4+2=rw)
		self.assertTrue(perm.permissions["r:alice"])
		self.assertTrue(perm.permissions["w:alice"])
		self.assertFalse(perm.permissions["x:alice"])

		# Group: r-- (4)
		self.assertTrue(perm.permissions["r:developers"])
		self.assertFalse(perm.permissions["w:developers"])
		self.assertFalse(perm.permissions["x:developers"])

		# Others: r--
		self.assertTrue(perm.permissions["r:*"])
		self.assertFalse(perm.permissions["w:*"])
		self.assertFalse(perm.permissions["x:*"])

	def test_chown(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")
		perm.chmod(0o744)  # user: r w x, group: r--, others: r--

		# Before chown
		self.assertTrue(perm.permissions["r:alice"])
		self.assertTrue(perm.permissions["w:alice"])
		self.assertTrue(perm.permissions["x:alice"])

		perm.chown("bob")

		# After chown, keys for alice should not exist
		self.assertNotIn("r:alice", perm.permissions)
		self.assertNotIn("w:alice", perm.permissions)
		self.assertNotIn("x:alice", perm.permissions)

		# Keys for bob should exist with the same values
		self.assertTrue(perm.permissions["r:bob"])
		self.assertTrue(perm.permissions["w:bob"])
		self.assertTrue(perm.permissions["x:bob"])

	def test_chgrp_existing_group(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")
		perm.chmod(0o740)  # user: r w x, group: r--, others: ---

		# Before chgrp
		self.assertTrue(perm.permissions["r:developers"])
		self.assertFalse(perm.permissions["w:developers"])
		self.assertFalse(perm.permissions["x:developers"])

		perm.chgrp("staff")

		# After chgrp, old group keys shouldn't exist
		self.assertNotIn("r:developers", perm.permissions)
		self.assertNotIn("w:developers", perm.permissions)
		self.assertNotIn("x:developers", perm.permissions)

		# New group keys should have the same values
		self.assertTrue(perm.permissions["r:staff"])
		self.assertFalse(perm.permissions["w:staff"])
		self.assertFalse(perm.permissions["x:staff"])

	def test_chgrp_when_no_group_existed(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice")
		# No group keys initially
		self.assertNotIn("r:developers", perm.permissions)

		# chgrp to create a group
		perm.chgrp("developers")

		# Now developers group keys should be True (as creation assigns True)
		self.assertTrue(perm.permissions["r:developers"])
		self.assertTrue(perm.permissions["w:developers"])
		self.assertTrue(perm.permissions["x:developers"])

	def test_set_permission(self):
		perm = UnixPermissions.make_permission(self.user_registry, "alice", "developers")
		# Ensure initial
		self.assertTrue(perm.permissions["r:developers"])

		# Now revoke read from developers
		perm.set_permission('r', 'developers', False)
		self.assertFalse(perm.permissions["r:developers"])

		# Add a new entity (not user, group or others) just to test functionality
		perm.set_permission('r', 'jane', True)
		self.assertTrue(perm.permissions["r:jane"])

	def test_persistence(self):
		perm = UnixPermissions("alice", "developers")

		packed = perm.to_transport()
		unpacked = BasicPersistentObject.from_transport(packed)

		# Check user keys
		self.assertTrue(unpacked.user_name, "alice")
		self.assertTrue(unpacked.permissions["r:alice"])
		self.assertTrue(unpacked.permissions["w:alice"])
		self.assertTrue(unpacked.permissions["x:alice"])

		# Check group keys
		self.assertTrue(unpacked.group_name, "developers")
		self.assertTrue(perm.permissions["r:developers"])
		self.assertTrue(perm.permissions["w:developers"])
		self.assertTrue(perm.permissions["x:developers"])

	def test_verify_permission(self):
		perm = UnixPermissions.make_permission(
			self.user_registry,
			"alice",
			"developers",
			mode=0o775
		)
		# permitted
		self.assertTrue(perm.is_right_granted(self.user_registry, "alice", "w"))     # owner write
		# bob is member of team and thus member of developers too
		self.assertTrue(perm.is_right_granted(self.user_registry, "bob", "w"))       # group write
		self.assertTrue(perm.is_right_granted(self.user_registry, "charly", "r"))    # other read

		# denied
		self.assertFalse(perm.is_right_granted(self.user_registry, "charly", "w"))   # other write
		self.assertFalse(perm.is_right_granted(self.user_registry, "unknown", "w"))  # invalid write
		self.assertFalse(perm.is_right_granted(self.user_registry, "unknown", "r"))  # invalid read


if __name__ == '__main__':
	unittest.main()
