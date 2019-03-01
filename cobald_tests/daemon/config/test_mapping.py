import random
import sys

import pytest

from collections import Counter
from cobald.daemon.config.mapping import Translator, ConfigurationError


def fqdn(obj):
    """Assign an fully qualified name to an object"""
    obj.fqdn = obj.__module__ + '.' + obj.__qualname__
    return obj


@fqdn
class Construct(object):
    """Type that stores its parameters on construction"""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return '%s(*%r, **%r)' % (self.__class__.__name__, self.args, self.kwargs)


@fqdn
def count(key):
    _counts[key] += 1
    return _counts[key]


_counts = Counter()


def counted(key):
    return {'__type__': count.fqdn, '__args__': [key]}


class SomeError(Exception):
    pass


@fqdn
def raises(exc=SomeError):
    raise exc('this is an error')


class TestTranslate(object):
    def test_load_name(self):
        translator = Translator()
        loaded_construct = translator.load_name(Construct.fqdn)
        assert loaded_construct is Construct
        loaded_module = translator.load_name(__name__)
        assert sys.modules[__name__] is loaded_module

    def test_construct(self):
        translator = Translator()
        for args in ((), [5, 2E7, -2, 27], range(5)):
            for kwargs in ({}, {'foo': 'bar', 'qux': 42},):
                obj = translator.construct({'__type__': Construct.fqdn, '__args__': args, **kwargs})
                assert isinstance(obj, Construct)
                assert obj.args == tuple(args)
                assert obj.kwargs == kwargs
                noargs_obj = translator.construct({'__type__': Construct.fqdn, **kwargs})
                assert not noargs_obj.args
                assert noargs_obj.kwargs == kwargs
                kw_obj = translator.construct({'__type__': Construct.fqdn, '__args__': args, **kwargs}, foo=42)
                assert kw_obj.kwargs['foo'] == 42

    def test_translate_primitives(self):
        translator = Translator()
        for value in ('foo', 'lasbfasfe', 1, 2, 1.0, 3.5, [], [1, 2, [3, 4]], {}, {'foo': 'bar', 'lst': [1, 2, 3]}):
            assert value == translator.translate_hierarchy(value)

    def test_translate_construct(self):
        translator = Translator()
        plain = translator.translate_hierarchy({'__type__': Construct.fqdn})
        assert isinstance(plain, Construct)
        nested = translator.translate_hierarchy([0, {'__type__': Construct.fqdn}, 2])
        assert isinstance(nested[1], Construct)
        stacked = translator.translate_hierarchy(
            [0, {'__type__': Construct.fqdn, 'child': {'__type__': Construct.fqdn}}, 2]
        )
        assert isinstance(stacked[1], Construct)
        assert isinstance(stacked[1].kwargs['child'], Construct)

    def test_translate_bottom_up(self):
        translator = Translator()
        plain = translator.translate_hierarchy(counted('plain'))
        assert plain == 1
        sequence = translator.translate_hierarchy([counted('sequence') for _ in range(5)])
        assert sequence == [item for item in range(5, 0, -1)]
        nested = translator.translate_hierarchy([
                [counted('nested') for _ in range(2)],
                *[counted('nested') for _ in range(2)],
                [counted('nested') for _ in range(2)]
        ])
        assert nested == [[6, 5], 4, 3, [2, 1]]

    def test_translate_error(self):
        translator = Translator()
        with pytest.raises(ConfigurationError) as err:
            translator.translate_hierarchy({'__type__': raises.fqdn}, where='test_translate_error')
        assert err.value.where == 'test_translate_error'
        # make sure errors propagate up without being raised anew
        with pytest.raises(ConfigurationError) as err:
            translator.translate_hierarchy([1, {'foo': {'__type__': raises.fqdn}}], where='test_translate_error')
        assert err.value.where == 'test_translate_error[1].foo'

    def test_lookup_failure(self):
        translator = Translator()
        with pytest.raises(ConfigurationError):
            translator.translate_hierarchy({
                '__type__': 'fake_module_%s.foo.bar' % random.getrandbits(32)
            })
        with pytest.raises(ConfigurationError):
            translator.translate_hierarchy({
                '__type__': '%s%s' % (Construct.fqdn, random.getrandbits(32))
            })
