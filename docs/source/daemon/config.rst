=======================
Component Configuration
=======================

Configuration of the :py:mod:`cobald.daemon` is performed at startup via one of two methods:
a YAML file or Python code.
While the former is more structured and easier to verify, the later allows for greater freedom.

The configuration file is the only positional argument when launching the :py:mod:`cobald.daemon`.
The file extension determines the type of configuration interface to use -
``.py`` for Python files and ``.yaml`` for YAML files.

.. code:: bash

    $ python3 -m cobald.daemon /etc/cobald/config.yaml
    $ python3 -m cobald.daemon /etc/cobald/config.py

The YAML Interface
==================

The top level of a YAML configuration file is a mapping with two sections:
the ``pipeline`` section setting up a pool control pipeline,
and the ``logging`` section setting up the logging facilities.
The ``logging`` section is optional and follows the standard
`configuration dictionary schema`_.

The ``pipeline`` section must contain a sequence of
:py:class:`~cobald.interface.Controller`\ s,
:py:class:`~cobald.interface.Decorator`\ s
and :py:class:`~cobald.interface.Pool`\ s.
Each ``pipeline`` is constructed in reverse order:
the *last* element should be a :py:class:`~cobald.interface.Pool`
and is constructed first,
then recursively passed to its predecessor to for construction.

.. code:: yaml

    # pool becomes the target of the controller
    pipeline:
        - !LinearController
          low_utilisation: 0.9
          high_utilisation: 1.1
        - !CpuPool
          interval: 1

Object References
*****************

YAML configurations support ``!!`` tag and ``!`` constructor syntax.
These allow to use arbitrary Python objects and registered plugins, respectively.
Both support keyword and positional arguments.

.. code:: yaml

    # generic python tag for arbitrary objects
    !!python/object:cobald.controller.linear.LinearController {low_utilisation: 0.9}
    # constructor tag for registered plugin
    !LinearController
    low_utilisation: 0.9

.. versionadded:: 0.9.3

.. seealso:: The `PyYAML`_ documentation on "YAML tags and Python types".

A legacy format using explicit type references is available, but discouraged.
This uses an invocation mechanism that can use arbitrary callables to construct objects:
each mapping with a ``__type__`` key is invoked with its items as keyword arguments,
and the optional ``__args__`` as positional arguments.

.. code:: yaml

    pipeline:
        # same as ``package.module.callable(a, b, keyword1="one", keyword2="two")
        - __type__: package.module.callable
          __args__:
            - a
            - b
          keyword1: one
          keyword2: two

.. deprecated:: 0.9.3
    Use YAML tags and constructors instead.

:note: To read the yaml configuration ``yaml.SafeLoader`` is used. See the
       `PyYAML`_ documentation for details.

Python Code Inclusion
=====================

Python configuration files are loaded like regular modules.
This allows to define arbitrary types and functions, and directly chain components or configure logging.
At least one :py:class:`~.cobald.daemon.service.service` should be instantiated.

.. _`configuration dictionary schema`: https://docs.python.org/3/library/logging.config.html#configuration-dictionary-schema

.. _`PyYAML`: https://pyyaml.org/wiki/PyYAMLDocumentation
