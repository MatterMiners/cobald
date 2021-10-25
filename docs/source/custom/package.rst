=================================
Using and Distributing Extensions
=================================

Extensions for :py:mod:`cobald` are regular Python code accessible to the interpreter.
For specific problems, extensions can be defined directly in a Python configuration file.
General purpose and reusable code should be made available as a Python package.
This ensures proper installation and dependency management,
and allows quick access from YAML configuration files.

Configuration Files
===================

Using Python :doc:`configuration files </source/daemon/config>` allows to define arbitrary
objects, functions and helpers.
This is ideal for minor modifications of existing objects and
experimental extensions.
Simply add new definitions to the configuration before using them:

.. code:: python3

    #/etc/cobald/my_demo.py
    from cobald.interface import Controller

    from cobald_demo.cpu_pool import CpuPool
    from cobald_demo.draw_line import DrawLineHook


    # custom Controller implementation
    class StaticController(Controller):
        """Controller that sets demand to a fixed value"""
        def __init__(self, target, demand):
            super().__init__(target)
            self.target.demand = demand

    # use custom Controller
    pipeline = StaticController.s(demand=50) >> DrawLineHook.s() >> CpuPool(interval=1)

Configuration files are easy to use and modify, but impractical for reusable extensions.

Python Packages
===============

For generic extensions, Python packages simplify distribution and reuse.
Packages are individual `.py` files or folders containing several `.py` files;
in addition, packages contain metadata for dependency management and installation.

.. code:: python3

    # my_controller.py
    from cobald.interfaces import Controller

    class StaticController(Controller):
        def __init__(self, target, demand):
            super().__init__(target)
            self.target.demand = demand

Packages can be temporarily accessed via ``PYTHONPATH`` or permanently installed.
Once available, packages can be imported and used in any configuration.

.. code:: python3

    #/etc/cobald/my_demo.py
    from my_controller import StaticController

    from cobald_demo.cpu_pool import CpuPool
    from cobald_demo.draw_line import DrawLineHook

    # use custom Controller from package
    pipeline = StaticController.s(demand=50) >> DrawLineHook.s() >> CpuPool(interval=1)

Packages require additional effort to create and use, but are easier to automate and maintain.
As with any package, authors should follow the `PyPA`_ recommendations for `python packaging`_.

The ``setup.py`` File
*********************

The ``setup.py`` file contains the metadata to install, update and manage a package.
For extension packages, it should contain a dependency on :py:mod:`cobald` and the
keywords should mention ``cobald`` for findability.

.. code:: python

    # setup.py

    setup(
        # dependency on `cobald` core package
        install_requires=[
            'cobald',
            ...
        ],
        # searchable on pypi index
        keywords='... cobald',
        ...
    )

.. _extension_config_plugins:

YAML Configuration Plugins
**************************

Packages may define two different types of plugins for the
:ref:`YAML configuration <yaml_configuration>` format:
readers for entire configuration sections, and
tags for individual configuration elements.

.. note::

    YAML Plugins only apply to the YAML configuration format.
    They have no effect if the Python configuration format is used.

YAML Tag Plugins
----------------

Tag Plugins allow to execute extensions as configuration elements
by using YAML tag syntax, such as ``!MyExtension``.
Extensions are treated as callables and
receive arguments depending on the type of their element:
mappings are used as keyword arguments,
and
sequences are used as positional arguments.

.. code:: YAML

    # resolves to ExtensionClass(foo=2, bar="Hello World!")
    - !MyExtension
      foo: 2
      bar: "Hello World!"
    # resolves to ExtensionClass(2, "Hello World!")
    - !MyExtension
      - 2
      - "Hello World!"

A packages can declare any callable as a Tag Plugin
by adding it to the ``cobald.config.yaml_constructors`` group of ``entry_points``;
the name of the entry is converted to a Tag when evaluating the configuration.
For example, a plugin class ``ExtensionClass`` defined in ``mypackage.mymodule``
can be made available as ``MyExtension`` in this way:

.. code:: python3

    setup(
        ...,
        entry_points={
            'cobald.config.yaml_constructors': [
                'MyExtension = mypackage.mymodule:ExtensionClass',
            ],
        },
        ...
    )

.. hint::

    Tag Plugins are primarily intended to add custom
    :py:class:`~cobald.interfaces.Controller`, :py:class:`~cobald.interfaces.Decorator`,
    and :py:class:`~cobald.interfaces.Pool` types for a COBalD ``pipeline``.
    If a plugin implements a :py:meth:`~cobald.interfaces.Controller.s` method,
    this is used automatically.

.. note::

    If a plugin requires eager loading of its YAML configuration,
    decorate it with :py:func:`cobald.daemon.plugins.yaml_tag`.

.. versionadded:: 0.12.3

    The :py:func:`cobald.daemon.plugins.yaml_tag` and eager evaluation.

Section Plugins
---------------

Section Plugins allow to accept and digest new configuration sections.
In addition, the ``cobald`` daemon verify that there are no unexpected
configuration sections to protect against typos and misconfiguration.
Extensions are entire top-level sections in the YAML file,
which are passed to the plugin after parsing and tag evaluation:

.. code:: YAML

    # standard cobald pipeline
    pipeline:
        - !DummyPool
    # passes [{'some_key': 'a', 'more_key': 'b'}, 'foobar', TagPlugin()]
    # to the Plugin requesting 'my_plugin'
    my_plugin:
      - some_key: a
        more_key: b
      - foobar
      - !TagPlugin

A packages can declare any callable as a Section Plugin
by adding it to the ``cobald.config.sections`` group of ``entry_points``;
the name of the entry is the top-level name of the configuration section.
For example, a plugin callable ``ConfigReader`` defined in ``mypackage.mymodule``
can request the configuration section ``my_plugin`` in this way:

.. code:: python3

    setup(
        ...,
        entry_points={
            'cobald.config.sections': [
                'my_plugin = mypackage.mymodule:ConfigReader',
            ],
        },
        ...
    )

.. note::

    If a plugin must always be covered by configuration,
    or should run before or after another plugin,
    decorate it with :py:func:`cobald.daemon.plugins.constraints`.

.. versionadded:: 0.12

    The :py:func:`cobald.daemon.plugins.constraints` and dependency resolution.

The ``cobald`` Namespace
************************

The top-level ``cobald`` package itself is a `namespace package`_.
This allows the COBalD developers to add, remove or split sub-packages.
In order to not conflict with the core development,
do *not* add your own packages to the ``cobald`` namespace.

.. _PyPA: https://www.pypa.io/en/latest/
.. _`python packaging`: https://packaging.python.org
.. _`namespace package`: https://packaging.python.org/guides/packaging-namespace-packages/#native-namespace-packages
