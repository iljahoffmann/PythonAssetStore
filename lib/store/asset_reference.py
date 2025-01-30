from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from lib.persistence import BasicPersistentObject, IPersistentObject
from lib.store.asset_interfaces import IAssetReference
from lib.store.update_context import UpdateContext


class AssetReference(IAssetReference, ABC):
    def __init__(self, name:str = None):
        self._name = name

    def ctor_parameter(self):
        return {'name': self.get_name()}

    def get_name(self):
        return self._name

    @staticmethod
    def of(some_thing:Any) -> IAssetReference|Sequence[IAssetReference]:
        def _make(_in):
            if isinstance(_in, int):
                return AssetById(_in)
            elif isinstance(_in, str):
                return AssetByPath(_in)
            elif hasattr(_in, 'get_id'):
                return AssetById(_in.get_id())
            elif isinstance(_in, IAssetReference):
                return _in

            raise ValueError(f'invalid conversion type: {_in.__class__}')

        if isinstance(some_thing, Sequence):
            return [_make(e) for e in some_thing]
        else:
            return _make(some_thing)


class AssetById(AssetReference, BasicPersistentObject):
    def __init__(self, asset_id: int, name:str = None):
        super().__init__(name)
        self._id = asset_id

    def ctor_parameter(self):
        result = super().ctor_parameter()
        result['asset_id'] = self._id
        return result

    def get_asset(self, context: UpdateContext) -> "Asset":
        return context.store.acquire(context, asset_id=self._id)


class AssetByPath(AssetReference, BasicPersistentObject):
    def __init__(self, path: str, name:str = None):
        super().__init__(name)
        self._path = path

    def ctor_parameter(self):
        result = super().ctor_parameter()
        result['path'] = self._path
        return result

    def get_asset(self, context: UpdateContext) -> "Asset":
        return context.store.acquire(context, path=self._path)
