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

The ``cobald`` library provides a framework and runtime for balancing opportunistic resources.
With its lightweight :doc:`model </source/model/overview>` for pools of resources and their composition,
it is easy to define and manage a large number of opportunistic resources.
At the heart of ``cobald`` is a minimal control model that condenses relevant features
to control resources in a scalable and dynamic way.

.. seealso:: The `cobald demo`_ is a minimal working toy example for using :py:mod:`cobald`.

The COBalD Resource Model
=========================

The ``cobald`` model for controlling resources is built on four simple types of primitives.
Two fundamental primitives represent the actual resources and the provisioning strategy:

* The adapter handling concrete resources is a :py:class:`~cobald.interfaces.Pool`.
  Each Pool merely communicates the total volume of resources and their overall fitness.

* The decision to add or remove resources is made by a :py:class:`~cobald.interfaces.Controller`.
  Each Controller only inspects the fitness of its Pools and adjusts their desired volume.

These two primitives are sufficient for direct control of simple resources.
It is often feasible to control several pools of resources separately.

.. graphviz::

    digraph graphname {
        graph [rankdir=LR, splines=lines, bgcolor="transparent"]
        labelloc = "b"
        controla, controlb [label=Controller]
        poola, poolb [label=Pool]
        subgraph cluster_0 {
            controla -> poola
            pencolor=transparent
            label = "Resource 1"
        }
        subgraph cluster_1 {
            controlb -> poolb
            pencolor=transparent
            label = "Resource 2"
        }
        poola -> controlb [style=invis]
    }

For complex tasks it may be necessary to combine resources or change their interaction and appearance.

* The details of managing resources are encoded by :py:class:`~cobald.interfaces.Decorator`\ s.
  Each Decorator translates between the specific :py:class:`~cobald.interfaces.Pool`\ s
  and the generic :py:class:`~cobald.interfaces.Controller`\ s.

* The combination of several resources is made by :py:class:`~cobald.interfaces.CompositePool`\ s.
  Each CompositePool handles several Pools, but gives the outward appearance of a single Pool.

All four primitives can be combined to express even complex resource and control scenarios.
However, there is always a :py:class:`~cobald.interfaces.Controller` on one end
and a :py:class:`~cobald.interfaces.Pool` on the other.
Since individual primitives can be combined and reused,
new use cases require only a minimum of new implementations.

.. graphviz::

    digraph graphname {
        graph [rankdir=LR, splines=lines, bgcolor="transparent"]
        labelloc = "b"
        controller [label=Controller]
        decoa, decob, decoc [label=Decorator]
        composite [label=Composite]
        poola, poolb [label=Pool]
        controller -> decoa -> composite
        composite -> decob -> poola
        composite -> decoc -> poolb
        pencolor=transparent
        label = "Resource 1 and 2"
    }

About
=====

The ``cobald`` project originates from research on providing Cloud resources for analysts of the LHC collaborations.
It supersedes past work on the `ROCED`_ Cloud resource provider,
generalising its goal of provisioning opportunistic resources.
Furthermore, it integrates recent research on minimal, succinct semantics for provisioning resources.

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
.. _`cobald demo`: https://github.com/MaineKuehn/cobald_demo
