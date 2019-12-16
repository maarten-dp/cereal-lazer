from collections.abc import Iterable


class LimitedMethodError(Exception): pass


def limitted_method(name, klass_name):
    msg = ('{} cannot be called on an emulated object. Define a (de)serializer'
           ' for the class {} in order to interract with it correctly')
    def method(*args, **kwargs):
        raise LimitedMethodError(msg.format(name, klass_name))
    return method


class EmulatedObject:
    def __init__(self, klass_name, callables):
        self.klass_name = klass_name
        for method in callables:
            setattr(self, method, limitted_method(method, klass_name))


def get_iterable_klass(cereal, iterable):
    iterator = [cereal.loads(a) for a in iterable]
    iterable = {
        '__iter__': lambda *x, **y: iter(iterator),
        '__next__': lambda *x, **y: iter(iterator).__next__()
    }
    return type('EmulatedObject', (EmulatedObject, ), iterable)


def naive_serializer(cereal, obj):
    result = {
        'class_name': obj.__class__.__name__,
        'callable': [],
        'attributes': {},
    }
    for attr_name in dir(obj):
        if attr_name.startswith('__'):
            continue
        attr = getattr(obj, attr_name)
        if callable(attr):
            result['callable'].append(attr_name)
        else:
            result['attributes'][attr_name] = cereal.dumps(attr)

    is_iterable = True
    try:
        iter(obj)
    except Exception:
        is_iterable = False

    if isinstance(obj, Iterable) or is_iterable:
        sequence = []
        for i in obj:
            sequence.append(cereal.dumps(i))
        result['iterable'] = sequence

    return result


def naive_deserializer(cereal, definition):
    EmulatedKlass = EmulatedObject
    if 'iterable' in definition:
        EmulatedKlass = get_iterable_klass(cereal, definition['iterable'])
    obj = EmulatedKlass(definition['class_name'], definition['callable'])
    for attr_name, attr in definition['attributes'].items():
        setattr(obj, attr_name, cereal.loads(attr))
    return obj

