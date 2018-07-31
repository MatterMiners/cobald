from cobald.daemon.config.mapping import construct


class Construct(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return '%s(*%r, **%r)' % (self.__class__.__name__, self.args, self.kwargs)


Construct.fqdn = Construct.__module__ + '.' + Construct.__qualname__


class TestHelpers(object):
    def test_construct(self):
        for args in ((), [5, 2E7, -2, 27], range(5)):
            for kwargs in ({}, {'foo': 'bar', 'qux': 42},):
                obj = construct({'__type__': Construct.fqdn, '__args__': args, **kwargs})
                assert isinstance(obj, Construct)
                assert obj.args == tuple(args)
                assert obj.kwargs == kwargs
                noargs_obj = construct({'__type__': Construct.fqdn, **kwargs})
                assert not noargs_obj.args
                assert noargs_obj.kwargs == kwargs
                kw_obj = construct({'__type__': Construct.fqdn, '__args__': args, **kwargs}, foo=42)
                assert kw_obj.kwargs['foo'] == 42
