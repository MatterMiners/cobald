from cobald.daemon.config.mapping import Translator


class Construct(object):
    """Type that stores its parameters on construction"""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return '%s(*%r, **%r)' % (self.__class__.__name__, self.args, self.kwargs)


Construct.fqdn = Construct.__module__ + '.' + Construct.__qualname__


class TestTranslate(object):
    def test_load_name(self):
        translator = Translator()
        loaded_construct = translator.load_name(Construct.fqdn)
        assert loaded_construct is Construct

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
