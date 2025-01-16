import re
from typing import MutableMapping

from lib.layered_dict import LayeredDict
from lib.persistence import BasicPersistentObject


class Entity(BasicPersistentObject):
	"""
	Class representing an entity (user, role or group) and their credentials.
	Credentials format: <right>:<entity_name>

	The special entity '*' is assigned to 'all'.

	ATTENTION: Entities must be setup before use by calling init_credentials() with a valid UserRegistry
	"""

	def ctor_parameter(self):
		return {'name': self.name, 'bases': self._inherits_from, 'meta': self.meta}

	def __init__(self, name: str, bases=None, meta=None, version=None, **kwargs):
		self.name = name

		# Assign default credentials on creation using LayeredDict in init_credentials()
		self.core_credentials = {
			f"r:{name}": True,
			f"w:{name}": True,
			f"x:{name}": True
		}
		self.credentials = None     # invalid until init_credentials - setting to None will throw when ill-used

		# Track entities added as permission layers
		self._inherits_from = bases if bases else []

		# remember the users metadata
		self.meta = meta if meta else kwargs

	def init_credentials(self, user_registry):
		self.credentials = LayeredDict(self.core_credentials)

		for base in self._inherits_from:
			entity = user_registry.get_entity(base)
			if entity.credentials is None:
				entity.init_credentials(user_registry)
			self.credentials.add_layer(entity.credentials, False)

		self.credentials.update_merged_layers()

	# std properties -> metadata
	def get_name(self):
		return self.meta.get('name')

	def set_name(self, name):
		self.meta['name'] = name
		return self

	def get_fullname(self):
		return self.meta.get('fullname')

	def set_fullname(self, name):
		self.meta['fullname'] = name
		return self

	def get_email(self):
		return self.meta.get('email')

	def set_email(self, email):
		self.meta['email'] = email
		return self

	def get_umask(self):
		return self.meta.get('umask')

	def set_umask(self, umask):
		self.meta['umask'] = umask
		return self

	# methods
	def set_credential(self, right: str, value: bool) -> None:
		"""
		Sets or updates a given right for the entity.

		:param right: The right to assign, e.g. 'r', 'w', 'x', etc.
		:param value: True to grant, False to revoke.
		"""
		key = f"{right}:{self.name}"
		self.credentials[key] = value

	def remove_credential(self, right: str) -> None:
		"""
		Removes the specified credential from the entity.

		:param right: The right to remove.
		"""
		key = f"{right}:{self.name}"
		if key in self.credentials:
			del self.credentials[key]

	def has_credential(self, right: str) -> bool:
		"""
		Checks if the entity has the specified credential.

		:param right: The right to check.
		:return: True if the credential is explicitly True, otherwise False.
		"""
		key = f"{right}:{self.name}"
		return self.credentials.get(key, False)

	def add_layer(self, entity) -> None:
		"""
		Adds another entity's credentials as a layer to this entity.

		:param entity: The entity whose credentials to add as a layer.
		"""
		self.credentials.add_layer(entity.credentials)
		self._inherits_from.append(entity.name)

	def add_guard_layer(self, entity) -> None:
		"""
		Adds another entity's credentials as a guard layer (inserted at index 0).

		:param entity: The entity whose credentials to add as a guard layer.
		"""
		self.credentials.insert_layer(0, entity.credentials)
		self._inherits_from.insert(0, entity.name)

	def remove_layer(self, entity) -> None:
		"""
		Removes a specific entity's credentials layer.

		:param entity: The entity whose credentials layer to remove.
		"""
		self.credentials.remove_layer(entity.credentials)
		if entity.name in self._inherits_from:
			self._inherits_from.remove(entity.name)

	def inherits_directly_from(self, other_entity_name:str) -> bool:
		return other_entity_name in self._inherits_from

	def inherits_from(self, registry, other_entity_name:str) -> bool:
		if other_entity_name in self._inherits_from:
			return True

		for parent_name in self._inherits_from:
			parent = registry.get_entity(parent_name)
			if parent and parent.inherits_from(registry, other_entity_name):
				return True

		return False


class UserRegistry(BasicPersistentObject):
	"""Class managing entities and their credentials."""

	def ctor_parameter(self):
		return {'entities': self.entities}

	USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')

	def __init__(self, entities:MutableMapping[str, Entity]=None, version=None):
		if entities:
			self.entities = entities
			for e in self.entities.values():
				e.init_credentials(self)
		else:
			self.entities: MutableMapping[str, Entity] = {}
			# create the 'all' entity - calling protected method here, because '*' is not a valid name normally
			# and the unsafe interface should not be exposed
			self._make_entity("*", mode=0o5777).init_credentials(self)

	def validate_name(self, name: str) -> bool:
		"""
		Validates the format of the name.

		:param name: The name to validate.
		:return: True if valid, False otherwise.
		"""
		return bool(self.USERNAME_PATTERN.match(name))

	def _make_entity(self, name: str, **kwargs) -> Entity|None:
		if name in self.entities:
			return None
		entity = Entity(name, **kwargs)
		self.entities[name] = entity
		return entity

	def make_entity(self, name: str, **kwargs) -> Entity|None:
		"""
		Creates a new entity with default credentials if it doesn't exist and name is valid.

		:param name: The desired name for the new entity.
		:param kwargs: assigned as metadata
		:return: the new instance if entity creation succeeded, None if invalid or already exists.
		"""
		if not self.validate_name(name):
			return None

		if entity := self._make_entity(name, **kwargs):
			entity.init_credentials(self)
			# inherit from 'all' entity
			self.add_layer_to_entity(name, "*")
			return entity

		return None

	def remove_entity(self, name: str) -> Entity|None:
		"""
		Removes an entity from the registry if it exists.

		:param name: The name of the entity to be removed.
		:return: the removed entity if it was successfully removed, None otherwise.
		"""
		if name == "*":
			raise PermissionError("this entity can not be deleted")

		if name not in self.entities:
			raise ValueError(f'unknown entity: {name}')

		to_remove = self.entities[name]

		# remove references to this entity from other entities ...
		for e in self.entities.values():
			if e.inherits_directly_from(name):
				e.remove_layer(to_remove)

		# ... then remove the entity itself
		del self.entities[name]
		return to_remove

	def has_right(self, name: str, right: str) -> bool:
		"""
		Checks if an entity has a specific right.

		:param name: The name whose right is being checked.
		:param right: The right to verify, e.g. 'r', 'w', 'x'.
		:return: True if the entity exists and the right is granted, False otherwise.
		"""
		entity = self.entities.get(name)
		if entity is None:
			return False
		return entity.has_credential(right)

	def grant_right(self, name: str, right: str) -> bool:
		"""
		Grants a specified right to an entity.

		:param name: The name of the entity to grant the right.
		:param right: The right to grant.
		:return: True if granted, False if entity doesn't exist.
		"""
		entity = self.entities.get(name)
		if entity is None:
			return False
		entity.set_credential(right, True)
		return True

	def revoke_right(self, name: str, right: str) -> bool:
		"""
		Revokes a specified right from an entity.

		:param name: The name of the entity to revoke the right.
		:param right: The right to revoke.
		:return: True if revoked, False if entity doesn't exist.
		"""
		entity = self.entities.get(name)
		if entity is None:
			return False
		entity.set_credential(right, False)
		return True

	def add_layer_to_entity(self, name: str, layer_name: str) -> bool:
		"""
		Adds another entity's credentials as a layer to the specified entity.

		:param name: The name of the target entity.
		:param layer_name: The name of the entity whose credentials will be added as a layer.
		:return: True if the layer was added, False otherwise.
		"""
		entity = self.entities.get(name)
		layer_entity = self.entities.get(layer_name)
		if entity is None or layer_entity is None:
			return False
		entity.add_layer(layer_entity)
		return True

	def add_guard_layer_to_entity(self, name: str, layer_name: str) -> bool:
		"""
		Adds another entity's credentials as a guard layer to the specified entity.

		:param name: The name of the target entity.
		:param layer_name: The name of the entity whose credentials will be added as a guard layer.
		:return: True if the guard layer was added, False otherwise.
		"""
		entity = self.entities.get(name)
		layer_entity = self.entities.get(layer_name)
		if entity is None or layer_entity is None:
			return False
		entity.add_guard_layer(layer_entity)
		return True

	def remove_layer_from_entity(self, name: str, layer_name: str) -> bool:
		"""
		Removes a specific entity's credentials layer from the specified entity.

		:param name: The name of the target entity.
		:param layer_name: The name of the entity whose credentials layer will be removed.
		:return: True if the layer was removed, False otherwise.
		"""
		entity = self.entities.get(name)
		layer_entity = self.entities.get(layer_name)
		if entity is None or layer_entity is None:
			return False
		entity.remove_layer(layer_entity)
		return True

	def is_known_entity(self, name):
		return name in self.entities

	def get_entity(self, name):
		return self.entities.get(name)

