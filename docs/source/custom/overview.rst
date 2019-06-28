========================================
Custom Controllers, Pools and Extensions
========================================

The :py:mod:`cobald.daemon` is capable of loading any modules and code importable
by its Python interpreter.
In addition, plugins can be registered for fast access in configuration files.
Extensions are integrated as classes that satisfy the :py:class:`~.Controller`,
:py:class:`~.Pool` or :py:class:`~.Decorator` interfaces.
Internally, extensions can be organized and implemented as required.

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    pool
    package
