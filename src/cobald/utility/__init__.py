class InvariantError(Exception):
    """An invariant is violated"""


def enforce(condition: bool, exception: BaseException = InvariantError()):
    """
    Enforce that ``condition`` is set by raising ``exception`` otherwise

    This is a replacement for ``assert`` statements as part of validation.
    It cannot be disabled with ``-O`` and may raise arbitrary exceptions.

    .. code:: Python

        def sqrt(value):
            condition(value > 0, ValueError('value must be greater than zero')
            return math.sqrt(value)
    """
    if not condition:
        raise exception


def pairwise(iterable):
    """Iterator yielding consecutive pairs from ``iterable``"""
    elements = iter(iterable)
    return zip(elements, elements)
