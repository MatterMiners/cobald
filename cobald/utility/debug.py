class NameRepr(object):
    """
    Lazy pretty formatter for name of objects
    """
    def __init__(self, target):
        self.target = target

    def __str__(self):
        target = self.target
        try:
            return target.__module__ + ':' + target.__qualname__
        except AttributeError:
            try:
                return target.__module__ + ':' + target.__name__
            except AttributeError:
                return target.__name__

    __repr__ = __str__
