from collections.abc import MutableMapping


class LayeredDict(MutableMapping):
    """A dictionary-like object that supports layered key-value storage.

    The LayeredDict allows merging multiple dictionaries (layers) while maintaining a separate
    current layer for modifications. Keys are resolved by first lookup in current layer,
    followed by lookups in each of the layers in their order.

    Attributes:
        current (dict): The current layer where modifications are directly applied.
        layers (list of dict): A list of dictionaries representing the layers.
        merged_layers (dict): The computed merged view of all layers and the current layer.
    """

    def __init__(self, current=None, layers=None):
        """
        Initialize the LayeredDict with optional current and layers.

        Args:
            current (dict, optional): The current layer of the LayeredDict. Defaults to an empty dictionary.
            layers (list of dict, optional): A list of initial layers. Defaults to an empty list.
        """
        self.current = current if current is not None else {}
        self.layers = layers if layers is not None else []
        self.merged_layers = {}
        self.update_merged_layers()

    def update_merged_layers(self):
        """
        Recompute merged_layers by combining all layers and the current layer.

        This method ensures that the merged_layers attribute reflects the current state
        of all layers and the current layer, with priority given to the current layer.
        """
        merged = {}
        for layer in reversed(self.layers):
            merged.update(layer)
        merged.update(self.current)
        self.merged_layers = merged

    def __getitem__(self, key):
        """
        Retrieve a value by key, searching in merged layers.

        Args:
            key (str): The key to look up.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not found in any layer.
        """
        if key in self.merged_layers:
            return self.merged_layers[key]
        raise KeyError(f"Key '{key}' not found in any layer.")

    def __setitem__(self, key, value):
        """
        Set a key-value pair in the current layer.

        Args:
            key (str): The key to set.
            value: The value to associate with the key.
        """
        self.current[key] = value
        self.merged_layers[key] = value

    def __delitem__(self, key):
        """
        Remove a key from the current layer.

        Args:
            key (str): The key to delete.

        Raises:
            PermissionError: If the key exists only in layers and not in the current layer.
            KeyError: If the key is not found.
        """
        if key in self.current:
            del self.current[key]
            self.update_merged_layers()
        elif key in self.merged_layers:
            raise PermissionError(f"Key '{key}' exists only in layers and cannot be removed.")
        else:
            raise KeyError(f"Key '{key}' not found.")

    def __contains__(self, key):
        """
        Check if a key exists in the merged layers.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return key in self.merged_layers

    def __len__(self):
        """
        Return the number of keys in the merged layers.

        Returns:
            int: The total number of unique keys.
        """
        return len(self.merged_layers)

    def __iter__(self):
        """
        Iterate over keys in the merged layers.

        Returns:
            Iterator[str]: An iterator over the keys in the merged layers.
        """
        return iter(self.merged_layers)

    def add_layer(self, layer, perform_merge=True):
        """
        Add a new layer at the end.
        For efficiency, when adding multiple layers, consider setting perform_merge=True only on the last one.

        Args:
            layer (dict): The layer to add.
            perform_merge (bool, optional): Whether to recompute merged_layers after adding the layer.
                Defaults to True.
        """
        self.layers.append(layer)
        if perform_merge:
            self.update_merged_layers()

    def insert_layer(self, index, layer, perform_merge=True):
        """
        Insert a new layer at a specific index.
        For efficiency, when adding multiple layers, consider setting perform_merge=True only on the last one.

        Args:
            index (int): The index at which to insert the layer.
            layer (dict): The layer to insert.
            perform_merge (bool, optional): Whether to recompute merged_layers after inserting the layer.
                Defaults to True.
        """
        self.layers.insert(index, layer)
        if perform_merge:
            self.update_merged_layers()

    def remove_layer(self, layer, perform_merge=True):
        """
        Remove a specific layer.
        For efficiency, when removing multiple layers, consider setting perform_merge=True only on the last one.

        Args:
            layer (dict): The layer to remove.
            perform_merge (bool, optional): Whether to recompute merged_layers after removing the layer.
                Defaults to True.

        Raises:
            ValueError: If the layer is not found.
        """
        if layer in self.layers:
            self.layers.remove(layer)
            if perform_merge:
                self.update_merged_layers()
        else:
            raise ValueError("Layer not found.")

    def enumerate_layers(self):
        """
        Return an enumeration of the layers.

        Returns:
            list of tuple: A list of tuples where each tuple contains the index and the corresponding layer.
        """
        return list(enumerate(self.layers))


# Example usage:
if __name__ == "__main__":
    # Create a layered dictionary
    layer1 = {"a": 1, "b": 2}
    layer2 = {"b": 3, "c": 4, "e": 9}
    current = {"c": 5, "d": 6}

    ld = LayeredDict(current=current, layers=[layer1, layer2])

    print(ld["a"])  # Output: 1 (from layer1)
    print(ld["b"])  # Output: 2 (from layer1)
    print(ld["c"])  # Output: 5 (from current)
    print(ld["d"])  # Output: 6 (from current)
    print(ld["e"])  # Output: 9 (from layer2)

    ld["e"] = 7  # Add to current
    print(ld["e"])  # Output: 7

    print("b" in ld)  # Output: True

    try:
        del ld["b"]
    except PermissionError as e:
        print(e)  # Output: Key 'b' exists only in layers and cannot be removed.

    ld.add_layer({"f": 8})
    print(ld["f"])  # Output: 8
