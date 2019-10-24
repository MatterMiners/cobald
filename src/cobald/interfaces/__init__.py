r"""
Interfaces for primitives of the :py:mod:`cobald` model

Each :py:class:`~.Pool` provides a varying number of resources.
A :py:class:`~.Controller` adjusts the number of resources that
a :py:class:`~.Pool` must provide.
Several :py:class:`~.Pool`\ s can be combined in a single
:py:class:`~.CompositePool` to appear as one.
To modify how a :py:class:`~.Pool` presents or digests data,
any number of :py:class:`~.PoolDecorator` may proceed it.

.. graphviz::

    digraph graphname {
        graph [rankdir=LR, splines=lines, bgcolor="transparent"]
        controller [label=Controller]
        composite [label=CompositePool]
        decoa [label=PoolDecorator]
        poola, poolb [label=Pool]
        controller -> decoa -> composite
        composite -> poola
        composite -> poolb
    }

"""
from ._composite import CompositePool
from ._controller import Controller
from ._pool import Pool
from ._proxy import PoolDecorator
from ._partial import Partial

__all__ = [
    cls.__name__ for cls in (Pool, PoolDecorator, Controller, CompositePool, Partial)
]
