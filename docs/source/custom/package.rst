==========================
Packaging and Distribution
==========================

Ideally, any custom code is made available as a regular Python package.
This ensures proper installation and dependency management.
Once installed, :py:mod:`cobald` can access and use such packages directly.

Writing the setup.py
--------------------

Packages for :py:mod:`cobald` can follow the `PyPA`_ recommendations for `python packaging`_.
Their ``setup.py`` file should contain a dependency on :py:mod:`cobald`.
Ideally, the keywords should contain `cobald` for findability.

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

There are currently no ``entry_points`` used by :py:mod:`cobald`.

.. _PyPA: https://www.pypa.io/en/latest/
.. _`python packaging`: https://packaging.python.org
