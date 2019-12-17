import datetime
from functools import partial
from itertools import permutations

import pytest
import pytz
from cereal_lazer.cereal import Cereal
from cereal_lazer.naive_serializing import LimitedMethodError

cr = Cereal()

to_test = [
    5, 5.5, 'test', [1, 'test', 6.7], {
        'test1': 5.5,
        'test2': 4,
        6: 'test3'
    }, True, False,
    datetime.date(2018, 1, 1),
    datetime.datetime(2018, 1, 1, tzinfo=pytz.UTC),
    datetime.datetime(2018, 1, 1), [1, 2, 3, 4, 5], [1, 'test', [2, 'test,1']],
    {
        1: 'test',
        'test': {
            2: 5.6
        },
        3: [1, 2]
    }, [datetime.date(2018, 1, 1),
        datetime.date(2018, 1, 2)], {
            'test': datetime.date(2018, 1, 1)
        }
]


@pytest.mark.parametrize('to_serialize', to_test)
def test_serialize(to_serialize):
    assert cr.loads(cr.dumps(to_serialize)) == to_serialize


class SomeObject:
    def __init__(self, a, wild, attribute):
        self.a = a
        self.wild = wild
        self.attribute = attribute

    def __eq__(self, other):
        c1 = self.a == other.a
        c2 = self.wild == other.wild
        c3 = self.attribute == other.attribute
        return c1 and c2 and c3

    def some_method(self):
        pass


def set_up_custom_type():
    def to_builtin(v):
        return (v.a, v.wild, v.attribute)

    def from_builtin(v):
        return SomeObject(v[0], v[1], v[2])

    cr.register_class(SomeObject.__name__, SomeObject, to_builtin,
                      from_builtin)
    return SomeObject


def test_serialize_custom_type():
    obj = set_up_custom_type()
    o = obj(1, 'test', [5.5, True])
    assert cr.loads(cr.dumps(o)) == o


def test_it_can_serialize_naively():
    cr = Cereal(serialize_naively=True)
    o = SomeObject(1, 'test', [5.5, True])
    dump = cr.dumps(o)
    res = cr.loads(dump)
    assert o.a == res.a
    assert o.wild == res.wild
    assert o.attribute == res.attribute
    assert o.__class__ != res.__class__
    with pytest.raises(LimitedMethodError):
        res.some_method()


def test_it_can_emulate_an_iterable():
    cr = Cereal(serialize_naively=True)

    class SomeObject():
        def __iter__(self):
            return iter([1, 2, 3, 4])

    o = SomeObject()
    res = cr.loads(cr.dumps(o))
    assert res.__class__.__name__ == 'EmulatedObject'
    assert list(res) == [1, 2, 3, 4]


class RaiseObject():
    def __init__(self, a):
        if isinstance(a, int):
            raise Exception('Some init exception')
        self.a = int(a)


def test_it_can_throw_a_load_error():
    cr = Cereal()
    o = RaiseObject('1')

    def to_builtin(v):
        return v.a

    def from_builtin(v):
        return RaiseObject(v)

    cr.register_class('RaiseObject', RaiseObject, to_builtin, from_builtin)
    expected = 'Some init exception'
    with pytest.raises(Exception, match=expected) as ex:
        res = cr.loads(cr.dumps(o))


def test_it_can_ignore_load_errors():
    cr = Cereal(serialize_naively=True, raise_load_errors=False)
    o = RaiseObject('1')

    def to_builtin(v):
        return v.a

    def from_builtin(v):
        return RaiseObject(v)

    cr.register_class('RaiseObject', RaiseObject, to_builtin, from_builtin)
    res = cr.loads(cr.dumps(o))
    assert res == {'__cereal_lazer__': ['RaiseObject', 1]}
