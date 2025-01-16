from abc import ABC
from lib.store.asset_interfaces import IAssetReference


class BasicAssetReference(IAssetReference, ABC):
    """
    Basic implementation of the IAssetReference interface.
    """

    def __init__(self, name=None):
        self.name = name

    def retrieve(self):
        """Retrieve the asset (to be implemented by derived classes)."""
        raise NotImplementedError()

    def get_name(self):
        return self.name

    def __str__(self):
        prefix = f"{self.name}:" if self.name else ""
        return f"{prefix}BasicAssetReference"


class AssetInstanceReference(BasicAssetReference):
    """
    A reference to a specific asset instance.
    """

    def __init__(self, asset=None, name=None):
        super().__init__(name)
        self.referee = asset

    def retrieve(self):
        if self.referee is None:
            raise ValueError("No asset is referenced.")
        return self.referee

    def to_tree(self):
        return {
            "type": "AssetInstanceReference",
            "name": self.name,
            "referee_id": self.referee.local_id if self.referee else None
        }

    def from_tree(self, tree):
        self.name = tree.get("name")
        # Assuming a method to retrieve assets by ID
        self.referee = retrieve_asset_by_id(tree.get("referee_id"))  # Placeholder function
        return self

    def __str__(self):
        if self.referee is None:
            return "nullReference"
        prefix = f"{self.name}:" if self.name else ""
        return f"{prefix}{self.referee.local_id}"


class AssetIdReference(BasicAssetReference):
    """
    A reference to an asset by its unique ID.
    """

    def __init__(self, asset_id=-1, name=None):
        super().__init__(name)
        self.asset_id = asset_id

    def retrieve(self):
        # Assuming a method to retrieve assets by ID
        return retrieve_asset_by_id(self.asset_id)  # Placeholder function

    def to_tree(self):
        return {
            "type": "AssetIdReference",
            "name": self.name,
            "asset_id": self.asset_id
        }

    def from_tree(self, tree):
        self.name = tree.get("name")
        self.asset_id = tree.get("asset_id")
        return self

    def __str__(self):
        prefix = f"{self.name}:" if self.name else ""
        return f"{prefix}{self.asset_id}"


class AssetKeyReference(BasicAssetReference):
    """
    A reference to an asset by a hierarchical key (e.g., a path).
    """

    def __init__(self, key=None, name=None):
        super().__init__(name)
        self.asset_key = key

    def retrieve(self):
        # Assuming a method to retrieve assets by key
        return retrieve_asset_by_key(self.asset_key)  # Placeholder function

    def to_tree(self):
        return {
            "type": "AssetKeyReference",
            "name": self.name,
            "key": self.asset_key
        }

    def from_tree(self, tree):
        self.name = tree.get("name")
        self.asset_key = tree.get("key")
        return self

    def __str__(self):
        prefix = f"{self.name}:" if self.name else ""
        return f"{prefix}{self.asset_key}"


# Placeholder functions for retrieving assets by ID or key
def retrieve_asset_by_id(asset_id):
    """Placeholder: Implement logic to retrieve an asset by its ID."""
    pass


def retrieve_asset_by_key(key):
    """Placeholder: Implement logic to retrieve an asset by its key."""
    pass
