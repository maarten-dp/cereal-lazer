from collections.abc import Iterable
from contextlib import contextmanager

DEPTH = 0


@contextmanager
def depth_context():
    # temp solution to recursion errors. Should ideally be replaced by a sort
    # of registry solution
    global DEPTH
    DEPTH += 1
    yield DEPTH
    DEPTH -= 1


class LimitedMethodError(Exception):
    pass


def limitted_method(name, klass_name):
    msg = ('{} cannot be called on an emulated object. Define a (de)serializer'
           ' for the class {} in order to interract with it correctly')

    def method(*args, **kwargs):
        raise LimitedMethodError(msg.format(name, klass_name))

    return method


def raise_when_called(exc):
    def decorated(*args, **kwargs):
        raise exc

    return decorated


class EmulatedObject:
    def __init__(self, definition):
        self.klass_name = definition['class_name']
        for method in definition['callable']:
            setattr(self, method, limitted_method(method, self.klass_name))


def get_emulated_klass(cereal, definition):
    attributes = {}
    if 'iterable' in definition:
        iterator = [cereal.loads(a) for a in definition['iterable']]
        attributes = {
            '__iter__': lambda *x, **y: iter(iterator),
            '__next__': lambda *x, **y: iter(iterator).__next__()
        }
    for attr_name, (msg, excklass) in definition.get('raisers', {}).items():
        exc = type(excklass, (Exception, ), {})
        attributes[attr_name] = property(raise_when_called(exc(msg)))
    klass_name = 'Emulated{}'.format(definition['class_name'])
    return type(klass_name, (EmulatedObject, ), attributes)


def naive_serializer(cereal, obj):
    with depth_context() as depth:
        if depth < cereal.max_naive_depth:
            return _naive_serializer(cereal, obj)
        return {
            'class_name': obj.__class__.__name__,
            'callable': [],
            'attributes': {},
            'raisers': {}
        }


def _naive_serializer(cereal, obj):
    result = {
        'class_name': obj.__class__.__name__,
        'callable': [],
        'attributes': {},
        'raisers': {}
    }
    for attr_name in dir(obj):
        if attr_name.startswith('__'):
            continue
        try:
            attr = getattr(obj, attr_name)
            if callable(attr):
                result['callable'].append(attr_name)
            else:
                result['attributes'][attr_name] = cereal.dumps(attr)
        except Exception as e:
            result['raisers'][attr_name] = (str(e), e.__class__.__name__)

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
    if isinstance(definition, dict) and 'class_name' in definition:
        EmulatedKlass = get_emulated_klass(cereal, definition)
        obj = EmulatedKlass(definition)
        for attr_name, attr in definition['attributes'].items():
            setattr(obj, attr_name, cereal.loads(attr))
        return obj
    return definition
