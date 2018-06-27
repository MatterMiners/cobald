"""
Interfaces for primitives of the :py:mod:`cobald` model

Each :py:class:`~.pool.Pool` provides a varying number of resources.
A :py:class:`~.controller.Controller` adjusts the number of resources that a :py:class:`~.pool.Pool` must provide.
Several :py:class:`~.pool.Pool` can be combined in a single :py:class:`~.composite.CompositePool` to appear as one.
To modify how a :py:class:`~.pool.Pool` presents or digests data,
any number of :py:class:`~.proxy.PoolDecorator` may proceed it.

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
