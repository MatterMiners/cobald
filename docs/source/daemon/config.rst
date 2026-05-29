=======================
Component Configuration
=======================

Configuration of the :py:mod:`cobald.daemon` is performed at startup via one of two methods:
a YAML file or Python code.
While the former is more structured and easier to verify, the latter allows for greater freedom.

The configuration file is the only positional argument when launching the :py:mod:`cobald.daemon`.
The file extension determines the type of configuration interface to use -
``.py`` for Python files and ``.yaml`` for YAML files.

.. code:: bash

    $ python3 -m cobald.daemon /etc/cobald/config.yaml
    $ python3 -m cobald.daemon /etc/cobald/config.py

.. _yaml_configuration:

The YAML Interface
==================

The top level of a YAML configuration file is a mapping with two sections:
the ``pipeline`` section setting up a pool control pipeline,
and the ``logging`` section setting up the logging facilities.
The ``logging`` section is optional and follows the standard
`configuration dictionary schema`_. [#dangling]_

The ``pipeline`` section must contain a sequence of
:py:class:`~cobald.interface.Controller`\ s,
:py:class:`~cobald.interface.Decorator`\ s
and :py:class:`~cobald.interface.Pool`\ s.
Each ``pipeline`` is constructed in reverse order:
the *last* element should be a :py:class:`~cobald.interface.Pool`
and is constructed first,
then recursively passed to its predecessor for construction.

.. code:: yaml

    # pool becomes the target of the controller
    pipeline:
        - !LinearController
          low_utilisation: 0.9
          high_utilisation: 1.1
        - !CpuPool
          interval: 1

High allocation: Increases number of drones if the allocation exceeds this value. It is calculated per machine type.
Low utilisation: Drains/reduces the number of drones if the utilisation falls below this value for a certain time.

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

.. note::

    The YAML configuration is read using ``yaml.SafeLoader`` to avoid arbitrary code execution.
    Objects must be marked as safe for loading,
    either as :ref:`COBalD plugins <extension_config_plugins>`
    or using `PyYAML`_ directly.

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

Python Code Inclusion
=====================

Python configuration files are loaded like regular modules.
This allows to define arbitrary types and functions, and directly chain components or configure logging.
At least one pipeline of :py:class:`~cobald.interface.Controller`\ s,
:py:class:`~cobald.interface.Decorator`\ s
and :py:class:`~cobald.interface.Pool`\ s should be instantiated.

.. code:: python3

    from cobald.controller.linear import LinearController

    from cobald_demo.cpu_pool import CpuPool
    from cobald_demo.draw_line import DrawLineHook

    pipeline = LinearController.s(
        low_utilisation=0.9, high_allocation=1.1
    ) >> CpuPool()

As regular modules, Python configurations must explicitly import the components they use.
In addition, everything not bound to a name will be garbage collected.
This allows configurations to use temporary objects, e.g. reading from files or sockets,
but means persistent objects (such as a pipeline) must be bound to a name.

.. [#dangling] YAML configurations allow for additional sections to configure plugins.
               Additional sections are :ref:`logged <daemon_logging>` to the
               ``"cobald.runtime.config"`` channel.

.. _`configuration dictionary schema`: https://docs.python.org/3/library/logging.config.html#configuration-dictionary-schema

.. _`PyYAML`: https://pyyaml.org/wiki/PyYAMLDocumentation
