from datetime import datetime
from threading import RLock
from typing import Self
from collections.abc import Sequence, Mapping
from xmlrpc.client import DateTime

from lib.path_op import path_get, path_set, path_del
from lib.persistence import BasicPersistentObject
from lib.call_result import ErrorResult
from lib.store.asset_interfaces import IAction, IAssetReference, IPermissionProvider
from lib.store.update_strategy import update_strategies
from lib.store.unix_permissions import UnixPermissions


# <<Data Entity>>
class Asset(BasicPersistentObject, IPermissionProvider):
    """
    Represents an asset with action, dependencies, update-logic and potential results.
    Concurrent access is managed using re-entrant locks (RLock) in all exposed methods.

    The core logic of an Asset is provided by its action, which uses the asset as its 'this' instance for all data.

    The asset's action defines purpose, interpretation and management of the asset's data and dependencies; to be 'make'
    compatible, the action must handle the dependencies accordingly. However, the action is free to
    use the IAssetReference dependencies and their name-lookup in any other way as well. Configuration of an
    update strategy ('updater'), that is not supported by the action, will result in an error. The asset uses 'basic'
    as default update strategy, which is supported by all actions. Only re-entrant or otherwise thread-safe actions can
    be used with parallel update strategies.

    All setter of Asset and the update() method return the asset instance for call-chaining.
    """
    def __init__(
            self,
            action:IAction=None,    # The action to perform (function or callable object).
            action_args:Mapping[str, object]=None,          # Arguments for the action.
            permissions: UnixPermissions=None,              # Access permissions for the asset
            local_id:int=-1,                # Local ID for the asset, equivalent to inode ID and assigned by the store.
            updater:str=None,                               # Update strategy (name of the update strategy).
            meta:Mapping[str, object]=None,                 # Asset meta-data, i.e. 'phony' for make update strategy.
            build_result=None,                              # Result of the build process.
            # build_error=None,                               # Errors during the build process.
            creation_date:DateTime=None,                    # Creation timestamp.
            last_modification:DateTime=None,                # Last modification timestamp.
            last_build:DateTime=None,                       # Last build timestamp.
            dependencies:Sequence[IAssetReference]=None,    # List of dependencies.
            asset_help:Mapping[str, str]=None,              # Help metadata.
            version:str=None,                               # from persistence
            **kwargs                                        # taken as actionArgs, if present
    ):
        self.action = action
        self.action_args = action_args or {}
        self.permissions = permissions
        if len(kwargs) > 0:
            self.action_args.update(kwargs)
        self.updater = updater or 'basic'
        self.meta = meta or {}
        self.build_result = build_result
        # self.build_error = build_error

        self.creation_date = creation_date or datetime.now()
        self.last_modification = last_modification
        self.last_build = last_build

        self.dependencies = dependencies or []
        self.named_dependencies = None  # Dictionary for quick lookup by name.

        self.asset_help = asset_help
        self._lock = RLock()  # Lock for thread-safe operations.
        self._local_id = local_id

    def ctor_parameter(self):
        with self._lock:
            return {
                'action': self.action,
                'action_args': self.action_args,
                'permissions': self.permissions,
                'local_id': self._local_id,
                'updater': self.updater,
                'meta': self.meta,
                'build_result': self.build_result,
                # 'build_error': self.build_error,
                'creation_date': self.creation_date,
                'last_modification': self.last_modification,
                'last_build': self.last_build,
                'dependencies': self.dependencies,
                'asset_help': self.asset_help,
            }

    def get_help(self):
        if self.asset_help:
            return self.asset_help
        else:
            return self.action.get_help()

    def get_permissions(self) -> "UnixPermissions":
        if self.permissions is None:
            raise ValueError("Asset is not completely initialized: permissions are missing")
        return self.permissions

    def set_permissions(self, permissions: "UnixPermissions"):
        self.permissions = permissions

    def get_id(self) -> int:
        with self._lock:
            return self._local_id

    def set_id(self, local_id) -> Self:
        with self._lock:
            self._local_id = local_id

        return self

    # Accessor methods
    def set_action(self, action) -> Self:
        with self._lock:
            self.action = action
            self._update_last_modification()
        return self

    def set_action_arguments(self, action_args) -> Self:
        with self._lock:
            self.action_args = action_args
            self._update_last_modification()
        return self

    def set_result(self, result) -> Self:
        with self._lock:
            self.build_result = result
            if result is not None:
                self._update_last_build()
        return self

    # def set_error(self, error) -> Self:
    #     with self._lock:
    #         self.build_error = error
    #     return self

    def get_result(self):
        with self._lock:
            return self.build_result

    # def get_error(self):
    #     with self._lock:
    #         return self.build_error

    def get_meta(self, key:str, default=None):
        with self._lock:
            if key is None:
                return self.meta

            lookup = key.replace('_', '.')
            return path_get(self.meta, lookup, default=default)

    def set_meta(self, **kwargs) -> Self:
        with self._lock:
            for key, value in kwargs.items():
                lookup = key.replace('_', '.')
                path_set(self.meta, lookup, value)
        return self

    def del_meta(self, key:str):
        with self._lock:
            lookup = key.replace('_', '.')
            return path_del(self.meta, lookup)

    # Dependency management
    def add_dependencies(self, *dependencies:Sequence[IAssetReference]):
        with self._lock:
            for dep in dependencies:
                self.dependencies.append(dep)
        return self

    def get_dependency_by_name(self, name:str):
        with self._lock:
            if not self.named_dependencies:
                self._build_named_dependency_lookup()
            if name in self.named_dependencies:
                return self.named_dependencies[name]
            raise KeyError(f"Dependency '{name}' not found.")

    def _build_named_dependency_lookup(self):
        self.named_dependencies = {dep.get_name(): dep for dep in self.dependencies if dep.get_name()}

    # Lifecycle methods
    def clone(self) -> Self:
        with self._lock:
            cloned = Asset(
                action=self.action,
                action_args=self.action_args.copy() if self.action_args else {},
                local_id=self._local_id,
                updater=self.updater,
                meta=self.meta.copy() if self.meta else {},
                build_result = self.build_result,
                # build_error = self.build_error,
                creation_date = self.creation_date,
                last_modification = datetime.now(),
                last_build = self.last_build,
                dependencies = self.dependencies.copy() if self.dependencies else [],
                asset_help = self.asset_help.copy() if self.asset_help else None,
                permissions=self.permissions
            )
            return cloned

    # <<no throw>>
    def update(self, context, **kwargs) -> Self:
        with self._lock:
            try:
                updater = update_strategies[self.updater]
                return updater.update(self, context, **kwargs)
            except Exception as ex:
                self.set_result(ErrorResult.from_exception(ex))
            return self

    # Error handling
    @staticmethod
    def error_from_exception(exception):
        return {
            "message": str(exception),
            "exception": type(exception).__name__,
            "stacktrace": exception.__traceback__
        }

    # Internal updates
    def _update_last_modification(self):
        self.last_modification = datetime.now()

    def _update_last_build(self):
        self.last_build = datetime.now()


if __name__ == '__main__':
    def main():
        from action import NoAction
        a1 = Asset(NoAction()).set_meta(make_phony=False)
        pa1 = a1.to_transport()
        upa1 = BasicPersistentObject.from_transport(pa1)
        pass

    main()
