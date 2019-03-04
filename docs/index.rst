===========================================
COBalD - the Opportunistic Balancing Daemon
===========================================

.. image:: https://readthedocs.org/projects/cobald/badge/?version=latest
    :target: http://cobald.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.org/MatterMiners/cobald.svg?branch=master
    :target: https://travis-ci.org/MatterMiners/cobald
    :alt: Test Status

.. image:: https://codecov.io/gh/MatterMiners/cobald/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/MatterMiners/cobald
    :alt: Test Coverage

.. image:: https://img.shields.io/pypi/v/cobald.svg
    :alt: Available on PyPI
    :target: https://pypi.python.org/pypi/cobald/

.. image:: https://img.shields.io/github/license/MatterMiners/cobald.svg
    :alt: License
    :target: https://github.com/MatterMiners/cobald/blob/master/LICENSE

.. image:: https://zenodo.org/badge/129873843.svg
   :alt: Zenodo DOI
   :target: https://zenodo.org/badge/latestdoi/129873843

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Contents:

    /source/model/overview
    /source/daemon/overview
    /source/custom/overview
    /source/glossary
    Module Index <source/api/modules>

.. image:: images/cobald_logo_120.png
    :alt: Cobald Logo
    :height: 150
    :align: right

The ``cobald`` is a lightweight framework to balance opportunistic resources:
cloud bursting, container orchestration, allocation scaling and more.
Its lightweight :doc:`model </source/model/overview>` for resources and their composition
makes it easy to integrate custom resources and manage them at a large scale.
The idea is as simple as it gets:

    | Start good things.
    | Stop bad things.

.. seealso:: The `cobald demo`_ is a minimal working toy example for using :py:mod:`cobald`.

Quick Info
==========

In the current state, ``cobald`` is a research and expert tool targeting administrators and developers.
You have to manually select your resource backends and compose the strategy.
Still, the simplicity of ``cobald`` should make it accessible for interested users as well.

*Getting COBalD up and running*

    Have a look at the `cobald demo`_.
    It provides a minimal working example for running COBalD.
    The demo shows you how to install, configure and run your own COBalD instance.

*Using COBalD to horizontally scale an HTCondor Pool*

    The `TARDIS`_ project provides backends to several cloud providers.
    This allows you to orchestrate prebuilt VM images.

About
=====

The ``cobald`` project originates from research on dynamically providing
Cloud resources for analysts of the LHC collaborations.
It supersedes past work on the `ROCED`_ Cloud resource provider,
generalising its goal of provisioning opportunistic resources.

The development of ``cobald`` is currently organized by the GridKa and CMS research groups at KIT.
We openly encourage adoption and contributions outside of KIT, LHC and our current selection of opportunistic resources.
Information on deployment as well as creating and publishing custom plugins will follow.

Please contact us on `github`_ or `gitter`_ if you want to contribute.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _github: https://github.com/MatterMiners/cobald
.. _ROCED: https://github.com/roced-scheduler/ROCED
.. _`cobald demo`: https://github.com/MaineKuehn/cobald_demo
.. _`TARDIS`: https://github.com/tardis-resourcemanager/tardis
.. _gitter: https://gitter.im/MatterMiners/community
