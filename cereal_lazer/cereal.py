from datetime import date, datetime
from functools import partial

import msgpack
import pytz

from .naive_serializing import naive_deserializer, naive_serializer

LIB_KEY = '__cereal_lazer__'


def default_encoder(cereal):
    if cereal.serialize_naively:
        return partial(naive_serializer, cereal)
    return lambda x: x


def default_decoder(cereal):
    if cereal.serialize_naively:
        return partial(naive_deserializer, cereal)
    return lambda x: x


class Cereal:
    def __init__(self, serialize_naively=False, raise_load_errors=True):
        self.to_format = {}
        self.from_format = {}
        self.registered_as = {}
        self.register_default()
        self.encoding_registry = {}
        self.encoding = False

        self.serialize_naively = serialize_naively
        self.raise_load_errors = raise_load_errors

    def register_class(self, name, klass, to_fn, from_fn):
        self.to_format[klass] = to_fn
        self.from_format[name] = from_fn
        self.registered_as[klass] = name

    def dumps(self, obj):
        return msgpack.packb(obj, default=self._encode).hex()

    def loads(self, content):
        content = bytes.fromhex(content)
        try:
            return msgpack.unpackb(
                content, object_hook=self._decode, encoding='utf-8')
        except Exception as e:
            if self.raise_load_errors:
                raise e
            return msgpack.unpackb(content, encoding='utf-8')

    def _decode(self, content):
        if isinstance(content, dict):
            if LIB_KEY in content:
                as_name, obj = content[LIB_KEY]
                from_fn = self.from_format.get(as_name, default_decoder(self))
                return from_fn(obj)
        return content

    def _encode(self, obj):
        klass = obj.__class__
        to_fn = self.to_format.get(klass, default_encoder(self))
        as_name = self.registered_as.get(klass, klass.__name__)
        return {LIB_KEY: (as_name, to_fn(obj))}

    def register_default(self):
        self.register_class(
            datetime.__name__, datetime,
            lambda x: (x.timetuple()[:-3], str(x.tzinfo) if x.tzinfo else None),
            lambda x: datetime(*x[0], tzinfo=pytz.timezone(x[1]) if x[1] else x[1]))
        self.register_class(date.__name__, date, lambda x: x.timetuple()[:3],
                            lambda x: date(*x))
