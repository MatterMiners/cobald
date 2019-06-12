========================================
Custom Controllers, Pools and Extensions
========================================

The :py:mod:`cobald.daemon` is capable of loading any modules and code importable by its Python interpreter.
Any :py:class:`~.Controller`, :py:class:`~.Pool` or :py:class:`~.Decorator`
is a regular class implementing the respective interface.
This gives significant freedom in how to organize and implement custom extensions.

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    pool
    package
