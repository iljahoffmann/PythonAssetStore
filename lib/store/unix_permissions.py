from collections.abc import MutableMapping
from lib.persistence import BasicPersistentObject
from lib.store.user_registry import UserRegistry


class UnixPermissions(BasicPersistentObject):
	def __init__(self, user, group=None, mode=None, version=None):
		"""
		Initialize a UnixPermissions instance.
		ATTENTION: use UnixPermissions.make() to create permissions, to ensure that user and group are valid.

		Args:
			user (str): The name of the user for whom permissions are being set.
			group (str, optional): The name of the group for whom permissions are being set. Defaults to None.
			mode (int or str, optional): A three-digit octal number specifying permissions. Defaults to None.
		"""
		self.user_name = user
		self.group_name = group
		self.permissions = {}

		if mode is not None:
			self.chmod(mode)
			return

		# Initialize the credential map, if no mode was given
		# Create user keys
		self.permissions = {
			f"r:{self.user_name}": True,
			f"w:{self.user_name}": True,
			f"x:{self.user_name}": True
		}

		# Create group keys if group is given at creation
		if self.group_name is not None:
			self.permissions[f"r:{self.group_name}"] = True
			self.permissions[f"w:{self.group_name}"] = True
			self.permissions[f"x:{self.group_name}"] = True

		# # Create others/all/* keys
		# self.permissions["r:*"] = True
		# self.permissions["w:*"] = True
		# self.permissions["x:*"] = True

	def ctor_parameter(self):
		return {'user': self.user_name, 'group': self.group_name, 'mode': self.permissions}

	@staticmethod
	def make_permission(user_registry, user_name, group_name=None, mode=None):
		"""
		Validate the user and group names and create a UnixPermissions instance.

		Args:
			user_registry (UserRegistry): A registry for validating users and groups.
			user_name (str): The name of the user.
			group_name (str, optional): The name of the group. Defaults to None.
			mode (int or str, optional): A three-digit octal number specifying permissions. Defaults to None.

		Returns:
			UnixPermissions: The created UnixPermissions instance.

		Raises:
			ValueError: If the user or group name is invalid.
		"""
		if not user_registry.is_known_entity(user_name):
			raise ValueError(f"Invalid user name: {user_name}")

		if group_name and not user_registry.is_known_entity(group_name):
			raise ValueError(f"Invalid group name: {group_name}")

		permission = UnixPermissions(user_name, group_name, mode)
		return permission

	@staticmethod
	def _decode_int_permissions(oct_value):
		"""
		Decode a single octal digit (0-7) into read, write, and execute booleans.

		Args:
			oct_value (int): An octal digit (0-7).

		Returns:
			tuple: A tuple of booleans (read, write, execute).
		"""
		r = bool(oct_value & 4)
		w = bool(oct_value & 2)
		x = bool(oct_value & 1)
		return r, w, x

	def chmod(self, mode):
		"""
		Change permissions using a three-digit octal number or colon-separated strings.

		Args:
			mode (int or str): A three- or four-digit octal number (e.g., 0o755 or '755')

		Raises:
			TypeError: If the mode is not an integer or valid octal string.
		"""
		if isinstance(mode, str):
			mode = int(mode, 8)
		elif isinstance(mode, MutableMapping):
			self.permissions = mode
			return
		elif not isinstance(mode, int):
			raise TypeError("Mode must be an int or octal string.")

		special_digit = (mode >> 9) & 0b111
		user_digit = (mode >> 6) & 0b111
		group_digit = (mode >> 3) & 0b111
		others_digit = mode & 0b111

		s, _, t = self._decode_int_permissions(special_digit)       # SetUID- and Sticky-Bit (group is ignored)
		u_r, u_w, u_x = self._decode_int_permissions(user_digit)
		g_r, g_w, g_x = self._decode_int_permissions(group_digit)
		o_r, o_w, o_x = self._decode_int_permissions(others_digit)

		self._set_user_permissions(u_r, u_w, u_x)

		if self.group_name is not None:
			self._set_group_permissions(g_r, g_w, g_x)

		self.permissions["r:*"] = o_r
		self.permissions["w:*"] = o_w
		self.permissions["x:*"] = o_x

		if special_digit != 0:
			self.permissions[f"s:*"] = s
			# set group is ignored
			self.permissions[f"t:*"] = t

	def chown(self, new_user_name):
		"""
		Change the username associated with permissions.

		Args:
			new_user_name (str): The new username.
		"""
		old_r = self.permissions.pop(f"r:{self.user_name}", True)
		old_w = self.permissions.pop(f"w:{self.user_name}", True)
		old_x = self.permissions.pop(f"x:{self.user_name}", True)

		self.user_name = new_user_name

		self.permissions[f"r:{self.user_name}"] = old_r
		self.permissions[f"w:{self.user_name}"] = old_w
		self.permissions[f"x:{self.user_name}"] = old_x

	def chgrp(self, new_group_name):
		"""
		Change the group name associated with permissions.

		Args:
			new_group_name (str): The new group name.
		"""
		if self.group_name is not None:
			old_r = self.permissions.pop(f"r:{self.group_name}", True)
			old_w = self.permissions.pop(f"w:{self.group_name}", True)
			old_x = self.permissions.pop(f"x:{self.group_name}", True)
		else:
			old_r = True
			old_w = True
			old_x = True

		self.group_name = new_group_name

		self.permissions[f"r:{self.group_name}"] = old_r
		self.permissions[f"w:{self.group_name}"] = old_w
		self.permissions[f"x:{self.group_name}"] = old_x

	def set_permission(self, right, entity, value):
		"""
		Set a specific permission for a user or group.

		Args:
			right (str): The permission type ('r', 'w', 'x', or extended).
			entity (str): The user or group name.
			value (bool): Whether the permission is granted.
		"""
		key = f"{right}:{entity}"
		self.permissions[key] = value

	def _set_user_permissions(self, r, w, x):
		"""
		Set permissions for the user.

		Args:
			r (bool): Read permission.
			w (bool): Write permission.
			x (bool): Execute permission.
		"""
		self.permissions[f"r:{self.user_name}"] = r
		self.permissions[f"w:{self.user_name}"] = w
		self.permissions[f"x:{self.user_name}"] = x

	def _set_group_permissions(self, r, w, x):
		"""
		Set permissions for the group.

		Args:
			r (bool): Read permission.
			w (bool): Write permission.
			x (bool): Execute permission.
		"""
		if self.group_name is not None:
			self.permissions[f"r:{self.group_name}"] = r
			self.permissions[f"w:{self.group_name}"] = w
			self.permissions[f"x:{self.group_name}"] = x

	def is_right_granted(self, user_registry, entity_name, right):
		"""
		Check if a specific permission is granted.

		Args:
			user_registry (UserRegistry): the registry, the permission is checked against.
			entity_name (str): the entity for which the permissions are evaluated.
			right (str): The permission type ('r', 'w', or 'x').

		Returns:
			bool: True if the permission is granted, False otherwise.
		"""
		entity = user_registry.get_entity(entity_name)
		if not entity:
			return False    # no access for unknown entities

		if (
			entity_name == self.user_name and
			self.permissions.get(f"{right}:{self.user_name}", False) and
			user_registry.has_right(self.user_name, right)
		):
			return True

		if (
			self.permissions.get(f"{right}:{self.group_name}", False) and
			entity.inherits_from(user_registry, self.group_name) and
			user_registry.has_right(self.group_name, right)
		):
			return True

		if user_registry.has_right("*", right) and self.permissions.get(f"{right}:*", False):
			return True

		return False

	def __str__(self):
		"""
		Get a string representation of the permissions.

		Returns:
			str: A string representation of the permissions' dictionary.
		"""
		return f'{self.user_name}/{self.group_name} {self.permissions}'

	def __repr__(self):
		"""
		Get a detailed string representation of the UnixPermissions instance.

		Returns:
			str: A detailed representation of the instance.
		"""
		return f"UnixPermissions(user={self.user_name}, group={self.group_name}, permissions={self.permissions})"

	def short_repr(self):
		def _flags_for(name):
			result = ''
			found = 0
			for r in ['r', 'w', 'x']:
				flag = '-'
				right_name = f'{r}:{name}'
				if right_name in self.permissions:
					if self.permissions.get(right_name):
						flag = r
					found += 1
				result += flag
			return result, found

		parts = []
		tested = 0
		for n in [self.user_name, self.group_name, '*']:
			flags, found_rights_count = _flags_for(n)
			tested += found_rights_count
			parts.append(flags)

		if len(self.permissions) > tested:
			parts.append('+')

		parts.extend([' ', self.user_name, ' ', self.group_name])
		return ''.join(parts)


if __name__ == '__main__':
	def main():
		p1 = UnixPermissions('bob', 'devs', 0o5775)
		r1 = p1.short_repr()
		packed1 = p1.to_transport()
		u1 = BasicPersistentObject.from_transport(packed1)
		pass

	main()
