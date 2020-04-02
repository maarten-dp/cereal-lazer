import inspect
import warnings
from datetime import date, datetime
from functools import partial

import msgpack
import pytz

from .naive_serializing import get_emulated_klass, naive_deserializer, naive_serializer

INSTANCE_KEY = '__cereal_lazer_instance__'
CLASS_KEY = '__cereal_lazer_class__'

RAISE_WARNING = ("Loading failed but raising the error is disabled. "
                 "Returning raw value: {}")
NAIVE_WARNING = ("Naive {} is enabled. Please consider registering a "
                 "valid type.")


def default_encoder(cereal):
    if cereal.serialize_naively:
        warnings.warn(NAIVE_WARNING.format('loading'))
        return partial(naive_serializer, cereal)
    return lambda x: x


def default_decoder(cereal):
    if cereal.serialize_naively:
        warnings.warn(NAIVE_WARNING.format('dumping'))
        return partial(naive_deserializer, cereal)
    return lambda x: x


class Cereal:
    def __init__(self,
                 serialize_naively=False,
                 raise_load_errors=True,
                 max_naive_depth=5):
        self.to_format = {}
        self.from_format = {}
        self.registered_as = {}
        self.class_from_name = {}
        self.register_default()
        self.max_naive_depth = max_naive_depth

        self.serialize_naively = serialize_naively
        self.raise_load_errors = raise_load_errors

    def register_class(self, name, klass, to_fn, from_fn):
        self.to_format[klass] = to_fn
        self.from_format[name] = from_fn
        self.registered_as[klass] = name
        self.class_from_name[name] = klass

    def dumps(self, obj):
        return msgpack.packb(obj, default=self._encode).hex()

    def loads(self, content):
        content = bytes.fromhex(content)
        try:
            return msgpack.unpackb(
                content, object_hook=self._decode, raw=False)
        except Exception as e:
            if self.raise_load_errors:
                raise e
            warnings.warn(RAISE_WARNING.format(e))
            return msgpack.unpackb(content, raw=False)

    def _decode(self, content):
        if isinstance(content, dict):
            if INSTANCE_KEY in content:
                as_name, obj = content[INSTANCE_KEY]
                from_fn = self.from_format.get(as_name, default_decoder(self))
                return from_fn(obj)
            if CLASS_KEY in content:
                as_name = content[CLASS_KEY]
                default = as_name
                if self.serialize_naively:
                    default = get_emulated_klass(self, {
                        'class_name': as_name,
                        'raisers': {}
                    })
                return self.class_from_name.get(as_name, default)
        return content

    def _encode(self, obj):
        if inspect.isclass(obj):
            return {CLASS_KEY: obj.__name__}
        klass = obj.__class__
        to_fn = self.to_format.get(klass, default_encoder(self))
        as_name = self.registered_as.get(klass, klass.__name__)
        return {INSTANCE_KEY: (as_name, to_fn(obj))}

    def register_default(self):
        self.register_class(
            datetime.__name__, datetime,
            lambda x: (x.timetuple()[:-3], str(x.tzinfo) if x.tzinfo else None),
            lambda x: datetime(*x[0], tzinfo=pytz.timezone(x[1]) if x[1] else x[1]))
        self.register_class(date.__name__, date, lambda x: x.timetuple()[:3],
                            lambda x: date(*x))
        self.register_class('set', set, lambda x: list(x), lambda x: set(x))
