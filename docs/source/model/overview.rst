==========================
Resource and Control Model
==========================

The goal of :py:mod:`cobald` is to simplify the provisioning of :term:`opportunistic resources`.
This is achieved with a composable model to define, aggregate, generalise and control resources.
The :py:mod:`cobald.interfaces` codify this into a handful of primitive building blocks.

Pool and Control Model
======================

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

Composition and Decoration
==========================

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



Detail Descriptions
===================

.. toctree::
    :maxdepth: 1

    pool_model
    control_pool
    compose_pools
