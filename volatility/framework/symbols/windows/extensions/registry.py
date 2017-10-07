from volatility.framework import objects, constants, exceptions
from volatility.framework.layers.registry import RegistryHive


class _CMHIVE(objects.Struct):
    @property
    def name(self):
        """Determine a name for the hive. Note that some attributes are
        unpredictably blank across different OS versions while others are populated,
        so we check all possibilities and take the first one that's not empty"""

        for attr in ["FileFullPath", "FileUserName", "HiveRootPath"]:
            try:
                return getattr(self, attr).String
            except (AttributeError, exceptions.InvalidAddressException):
                pass

        return None


class _CM_KEY_NODE(objects.Struct):
    """Extension to allow traversal of registry keys"""

    @property
    def subkeys(self):
        hive = self._context.memory[self.vol.layer_name]
        if not isinstance(hive, RegistryHive):
            raise TypeError("CM_KEY_NODE was not instantiated on a RegistryHive layer")
        for index in range(2):
            subkey_node = hive.get_cell(self.SubKeyLists[index]).u.KeyIndex
            # The keylist appears to include 4 bytes of key name after each value
            # We can either double the list and only use the even items, or
            # We could change the array type to a struct with both parts
            subkey_node.List.count = subkey_node.Count * 2
            for key_offset in subkey_node.List[::2]:
                yield hive.get_node(key_offset)

    @property
    def values(self):
        """Returns a list of the Value nodes for a key"""
        hive = self._context.memory[self.vol.layer_name]
        if not isinstance(hive, RegistryHive):
            raise TypeError("CM_KEY_NODE was not instantiated on a RegistryHive layer")
        child_list = hive.get_cell(self.ValueList.List)
        child_list.count = self.ValueList.Count
        for v in child_list:
            if v != 0:
                node = hive.get_node(v)
                if node.vol.type_name.endswith(constants.BANG + '_CM_KEY_VALUE'):
                    yield node

    @property
    def keyname(self):
        return self.Name.cast("string", max_length = self.NameLength, encoding = "latin-1")
