===========================================
COBalD - the Opportunistic Balancing Daemon
===========================================

.. image:: https://readthedocs.org/projects/cobald/badge/?version=latest
    :target: http://cobald.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.org/MaineKuehn/cobald.svg?branch=master
    :target: https://travis-ci.org/MaineKuehn/cobald
    :alt: Test Status

.. image:: https://codecov.io/gh/MaineKuehn/cobald/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/MaineKuehn/cobald
    :alt: Test Coverage

.. image:: https://img.shields.io/pypi/v/cobald.svg
    :alt: Available on PyPI
    :target: https://pypi.python.org/pypi/cobald/

.. image:: https://img.shields.io/github/license/MaineKuehn/cobald.svg
    :alt: License
    :target: https://github.com/MaineKuehn/cobald/blob/master/LICENSE.txt

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    /source/model/overview
    /source/daemon/overview
    /source/glossary
    Module Index <source/api/modules>

.. image:: images/cobald_logo.svg
    :alt: Cobald Logo
    :height: 150
    :align: left

The ``cobald`` library provides a framework and runtime for balancing opportunistic resources.
With its straightforward :doc:`model </source/model/overview>` for pools of resources and their composition,
it is easy to define and manage a large number of opportunistic resources.
At the heart of ``cobald`` is a minimal control model that condenses the desirable *and* feasible features
to control resources in a scalable and dynamic way.

Background
==========

The ``cobald`` project originates from research on providing Cloud resources for analysts of the LHC collaborations.
It supersedes past work on the `ROCED`_ Cloud resource provider,
generalising its goal of provisioning opportunistic resources.
Furthermore, it integrates recent research on minimal, succinct semantics for provisioning resources.

The major goal of ``cobald`` is to explicitly reflect our two main conclusions from past research:

    1. It is futile to categorize resources by their nature. The only feasible information is actual usage.
    2. It is futile to predict future usage and requirements. The only reliable information is what happens now.

About
=====

The development of ``cobald`` is currently organized by the GridKa and CMS research groups at KIT.
We openly encourage adoption and contributions outside of KIT, LHC and our current selection of opportunistic resources.
Information on deployment as well as creating and publishing custom plugins will follow.

Please contact us on `github`_ if you want to contribute already.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _github: https://github.com/MaineKuehn/cobald
.. _ROCED: https://github.com/roced-scheduler/ROCED
