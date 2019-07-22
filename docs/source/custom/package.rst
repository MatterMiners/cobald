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

Configuration Plugins
*********************

Packages can declare callables as plugins for the YAML configuration format.
Plugins are added as ``entry_points`` of the ``cobald.config.yaml_constructors`` group,
with a name to be used in configurations.
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

This allows using the extension as elements with YAML tag syntax,
such as ``!MyExtension``.
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


The ``cobald`` Namespace
************************

The top-level ``cobald`` package itself is a `namespace package`_.
This allows the COBalD developers to add, remove or split sub-packages.
In order to not conflict with the core development,
do *not* add your own packages to the ``cobald`` namespace.

.. _PyPA: https://www.pypa.io/en/latest/
.. _`python packaging`: https://packaging.python.org
.. _`namespace package`: https://packaging.python.org/guides/packaging-namespace-packages/#native-namespace-packages
