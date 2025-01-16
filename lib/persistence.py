import os
import json
import inspect
from datetime import datetime, timedelta
from queue import PriorityQueue
from abc import ABC, abstractmethod
from lib.module_loader import get_module
from lib.ABC import AbstractBaseClassCalled
from lib.project_path import SystemPath
from lib.nothing import nothing
from lib.bytes_conversions import encode_to_base64, decode_from_base64, bytes_to_str, str_to_bytes,\
    bytearray_to_str, str_to_bytearray


json_native_types = set([str, int, float, dict, list, bool, type(None)])


path_engine = SystemPath
runtime_path = SystemPath.local('[]')


class IPersistent(ABC):
    @abstractmethod
    def to_json(self):
        """
        Convert this object into it's json representation
        The result is most likely a dict, but can be of any type, that is supported by json.

        Also, the implementation may return nodes, that require a dedicated interpretation: i.e.
        StdJasonSerializable will include class-ctor references and ctor-parameters for embedded object
        instances.
        """
        pass

    @classmethod
    @abstractmethod
    def from_json(cls, tree):
        """
        Construct an object from it's json-representation (result is the constructed object)
        @parameter: an object as created by cls.to_json()
        """
        pass


class IPersistentObject(IPersistent, ABC):
    """Convert from and to: JSON tree <-> packed format"""
    @abstractmethod
    def to_transport(self):
        pass

    @classmethod
    @abstractmethod
    def from_transport(cls, packed_json):
        pass

    @abstractmethod
    def ctor_parameter(self):
        pass


class StdJSONSerializable(IPersistentObject):
    """
    A standard implementation for classes, whose instances can be completely initialized with __init__()

    Attention: required modules are reloaded and may result in new type instances, thus

        type(some_serializable) == type(some_serializable.__class__.from_transport(some_serializable.to_transport()))

    may result in False.
    """
    class ObjectEncoder(json.JSONEncoder):
        """
        Used as converter object -> json, i.e.:
        json_encoded_model = json.dumps(model, cls=StdJSONSerializable.ObjectEncoder)
        """

        def default(self, obj):
            obj_type = type(obj)
            if obj_type in json_native_types:
                result = json.JSONEncoder.default(self, obj)
            elif hasattr(obj, 'to_json'):
                result = obj.to_json()
            elif ExternalTypes.convertible(obj_type):
                converter = ExternalTypes.converter_for_type(obj_type)
                result = converter.convert_to_json(obj)
            else:
                raise ValueError(f'{obj} is not json-serializable.')

            return result

    class _ObjectDecoder:
        """
        Used as converter json -> object, i.e.:
        model = json.loads(json_encoded_model, object_hook=StdJSONSerializable.ObjectDecoder)
        """
        def object_hook(self, obj):
            if 'object_source' in obj:
                info = obj['object_source']
                if info is None:
                    info = nothing.code_info()
                source_path = path_engine.local(info[0])
                module = get_module(source_path)
                source_class = getattr(module, info[1], None)
                if source_class is None:
                    print(f'WARNING: class not found: {info[0]}.{info[1]}')
                    return obj

                if getattr(source_class, 'from_json', False):
                    converted = source_class.from_json(info[3], info[2])
                    return converted

                result = source_class(**info[3])
                return result
            else:
                return obj

        def __call__(self, obj):    # from orthogonal access to encoder and decoder
            result = self.object_hook(obj)
            return result

    # for orthogonal access to encoder and decoder
    ObjectDecoder = _ObjectDecoder()

    @abstractmethod
    def ctor_parameter(self):
        """
        Concrete classes need to overwrite this function to return a dictionary of the form
        { __init__parameter_name: parameter_value }, providing all parameter required to
        construct a completely initialized object by calling __init__().

        Example:
                class Foo(StdJSONSerializeable):
                        def __init__(self, name):          # one parameter named 'name' required
                                self._name = name

                        def ctor_parameter(self):
                                return {'name': self._name}    # provide the parameter's name and its value
        """
        pass

    @staticmethod
    def no_ctor_parameter():                        # for enhanced clarity in ctor_parameter()
        return {}

    def to_json(self, as_system_path=False):
        module_path = inspect.getabsfile(self.__class__)
        portable_module_path = path_engine.portable(module_path)
        class_name = self.__class__.__qualname__
        module = inspect.getmodule(self.__class__)
        version = getattr(module, '__version__', None)
        parameter = self.ctor_parameter()
        result = {
            'object_source': [portable_module_path, class_name, version, parameter]
        }
        return result

    def to_transport(self, **kwargs):
        """
        Returns a serialized encoding for this object.
        Optional parameter:
        'preparer': if set, gets called before the serialization begins - must return the object to be serialized.
        'packer': if set, applied to the serialized object - must return an (encoded) serialized object.
        """
        object_reference = self
        if 'preparer' in kwargs:
            preparer = kwargs['preparer']
            object_reference = preparer(self, **kwargs)
        indent = kwargs.get('indent', '\t')
        json_encoded = json.dumps(
            object_reference, cls=StdJSONSerializable.ObjectEncoder, indent=indent)
        transport_encoded = json_encoded
        if 'packer' in kwargs:
            packer = kwargs['packer']
            if packer:
                transport_encoded = packer(json_encoded)
        return transport_encoded

    @classmethod
    def from_json(cls, parameter, version):
        if len(parameter) == 0:
            created = cls()
        else:
            try:
                parameter['version'] = version
                created = cls(**parameter)
            except Exception as ex:
                print(f"from_json({str(cls)}): {str(ex)}")
                raise

        return created

    @classmethod
    def from_transport(cls, json_encoded, **kwargs):
        """
        Returns an object based on its serialized representation.
        Optional parameter:
        'unpacker': if set, applied to obtain the serialized object - must return an (decoded) serialized object.
        'finisher': if set, gets called with the serialization result - must return the result object for the operation.
        """
        if json_encoded is None:
            return None

        transport_decoded = json_encoded
        if 'unpacker' in kwargs:
            unpacker = kwargs['unpacker']
            transport_decoded = unpacker(
                transport_decoded) if unpacker else transport_decoded

        result = json.loads(transport_decoded,
                            object_hook=StdJSONSerializable.ObjectDecoder)
        if 'finisher' in kwargs:
            finisher = kwargs['finisher']
            result = finisher(result, **kwargs)

        return result

    def clone(self):
        """
        Create a deep copy of this serializable and its registered contents (value, children and tags)
        """
        packed = self.to_transport()
        result = self.__class__.from_transport(packed)
        return result

    def children_dict(self):
        result = {k: self[k] for k in self}
        return result


# more intuitive naming
class BasicPersistentObject(StdJSONSerializable):
    pass


def to_json(_object, dumped=True, **kwargs):
    _result = None
    if getattr(_object, 'to_json', False):
        _result = json.dumps(
            _object.to_json(), cls=StdJSONSerializable.ObjectEncoder, **kwargs)
    elif type(_object) in json_native_types:
        _result = _object if not dumped else json.dumps(
            _object, cls=StdJSONSerializable.ObjectEncoder, **kwargs)
    else:
        _result = json.dumps(
            _object, cls=StdJSONSerializable.ObjectEncoder, **kwargs)

    return _result


def from_json(json_encoded_string):
    result = StdJSONSerializable.from_transport(json_encoded_string)
    return result


def write_serializable(filename, serializable, permissions=0o622, **kwargs):
    def _opener(path, flags):
        return os.open(path, flags, permissions)

    with open(filename, 'w', opener=_opener) as f:
        packed_model = serializable.to_transport(**kwargs)
        f.write(packed_model)


def read_serializable(filename, **kwargs):
    try:
        with open(filename, 'r') as f:
            packed_object = f.read()
            result = StdJSONSerializable.from_transport(
                packed_object, **kwargs)
            return result
    except Exception as ex:
        print(f"read_serializable(): Error: {ex}")
        raise
        # return None


class ExternalTypes:
    type_to_ctor = {}

    @classmethod
    def register_type_conversion(cls, external_type, converter):
        ExternalTypes.type_to_ctor[external_type] = converter

    @classmethod
    def register_type_conversions(cls, external_type_to_converter_list):
        for external_type, converter in external_type_to_converter_list:
            ExternalTypes.register_type_conversion(external_type, converter)

    @classmethod
    def convertible(cls, external_type):
        return ExternalTypes.converter_for_type(external_type) is not None

    @classmethod
    def converter_for_type(cls, external_type):
        return ExternalTypes.type_to_ctor.get(external_type, None)


class ExternalSerializer(StdJSONSerializable):
    def convert_to_json(self, external_object):
        raise AbstractBaseClassCalled()


class DatetimeSerializer(ExternalSerializer):
    def __init__(self, timestamp):
        self._timestamp = timestamp

    def ctor_parameter(self):
        return {'timestamp': self._timestamp}

    @staticmethod
    def convert_to_json(datetime_instance):
        ctor = DatetimeSerializer(datetime_instance.timestamp())
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = datetime.fromtimestamp(parameter['timestamp'])
        return result


ExternalTypes.register_type_conversion(datetime, DatetimeSerializer)


# class TorchTypeSerializer(ExternalSerializer):
#
#     types = {
#         'torch.bfloat16': torch.bfloat16,
#     }
#
#     def __init__(self, torch_dtype):
#         self._torch_dtype = torch_dtype
#
#     def ctor_parameter(self):
#         return {'torch_dtype': self._torch_dtype}
#
#     @staticmethod
#     def convert_to_json(torch_type):
#         ctor = TorchTypeSerializer(str(torch_type))
#         as_json = ctor.to_json()
#         return as_json
#
#     @classmethod
#     def from_json(cls, parameter, version):
#         if parameter['torch_dtype'] in TorchTypeSerializer.types.keys():
#             return TorchTypeSerializer.types[parameter['torch_dtype']]
#         else:
#             raise ValueError(f"Unknown torch type: {parameter['torch_dtype']}")
#
#
# ExternalTypes.register_type_conversion(dtype, TorchTypeSerializer)


class TimedeltaSerializer(ExternalSerializer):
    def __init__(self, seconds):
        self._seconds = seconds

    def ctor_parameter(self):
        return {'seconds': self._seconds}

    @staticmethod
    def convert_to_json(timedelta_instance):
        ctor = TimedeltaSerializer(timedelta_instance.total_seconds())
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = timedelta(seconds=parameter['seconds'])
        return result


ExternalTypes.register_type_conversion(timedelta, TimedeltaSerializer)


# class OrderedSetSerializer(ExternalSerializer):
# 	def __init__(self, elements):
# 		self._elements = elements
#
# 	def ctor_parameter(self):
# 		return {'elements': self._elements}
#
# 	@staticmethod
# 	def convert_to_json(set_instance):
# 		ctor = OrderedSetSerializer([_ for _ in set_instance])
# 		as_json = ctor.to_json()
# 		return as_json
#
# 	@classmethod
# 	def from_json(cls, parameter, version):
# 		result = OrderedSet(parameter['elements'])
# 		return result
#
#
# ExternalTypes.register_type_conversion(OrderedSet, OrderedSetSerializer)


class SetSerializer(ExternalSerializer):
    def __init__(self, elements):
        self._elements = elements

    def ctor_parameter(self):
        return {'elements': self._elements}

    @staticmethod
    def convert_to_json(set_instance):
        ctor = SetSerializer([_ for _ in set_instance])
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = set(parameter['elements'])
        return result


ExternalTypes.register_type_conversion(set, SetSerializer)


class PriorityQueueSerializer(ExternalSerializer):
    def __init__(self, queue):
        self._queue = queue

    def ctor_parameter(self):
        return {'queue': self._queue.queue}

    @staticmethod
    def convert_to_json(queue):
        ctor = PriorityQueueSerializer(queue)
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = PriorityQueue()
        for entry in parameter['queue']:
            result.put(entry)
        return result


ExternalTypes.register_type_conversion(PriorityQueue, PriorityQueueSerializer)


class BytesSerializer(ExternalSerializer):
    def __init__(self, data: bytes):
        self.data = data

    def ctor_parameter(self):
        return {'data': self.data}

    @staticmethod
    def convert_to_json(data):
        ctor = BytesSerializer(bytes_to_str(encode_to_base64(data, mapping='urlsafe')))
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = decode_from_base64(str_to_bytes(parameter['data']))
        return result


ExternalTypes.register_type_conversion(bytes, BytesSerializer)


class BytearraySerializer(ExternalSerializer):
    def __init__(self, data: bytearray):
        self.data = data

    def ctor_parameter(self):
        return {'data': self.data}

    @staticmethod
    def convert_to_json(data):
        ctor = BytearraySerializer(bytearray_to_str(encode_to_base64(data, mapping='urlsafe')))
        as_json = ctor.to_json()
        return as_json

    @classmethod
    def from_json(cls, parameter, version):
        result = decode_from_base64(str_to_bytearray(parameter['data']), mapping='urlsafe')
        return result


ExternalTypes.register_type_conversion(bytearray, BytearraySerializer)


if __name__ == '__main__':
    import sys
    from datetime import datetime

    def main():
        some_json = {'a': 1, 'b': None, 'c': [1, 'x'], 'd': datetime.now(), 'e': bytearray(b'Hello World')}
        packed = to_json(some_json)
        module_path = SystemPath.as_module_path("[]/lib/persistence.py")
        [print(_) for _ in sys.modules]
        print(f'{"persistence" in sys.modules}')
        unpacked = from_json(packed)
        print(f'{"persistence" in sys.modules}')
        unpacked2 = from_json(packed)
        pass

    main()
    sys.exit(0)

