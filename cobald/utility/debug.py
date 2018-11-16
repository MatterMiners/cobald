from types import ModuleType

from functools import partial, singledispatch


@singledispatch
def pretty_ref(obj):
    return obj.__module__ + ':' + obj.__qualname__


@pretty_ref.register(partial)
def pretty_partial(obj):
    if not obj.args and not obj.keywords:
        return pretty_ref(obj.func)
    return 'partial(%s%s%s)' % (
        pretty_ref(obj.func),
        '' if not obj.args else ', '.join(repr(arg) for arg in obj.args),
        '' if not obj.keywords else ', '.join('%r = %r' % (k, v) for k, v in obj.keywords.items()),
    )


@pretty_ref.register(ModuleType)
def pretty_module(obj):
    return obj.__name__


class NameRepr(object):
    """
    Lazy pretty formatter for name of objects
    """
    def __init__(self, target):
        self.target = target

    def __str__(self):
        target = self.target
        return pretty_ref(target)

    __repr__ = __str__
