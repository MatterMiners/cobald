==============================
Resource Abstraction via Pools
==============================

The fundamental abstraction for resources is the :py:class:`~cobald.interfaces.pool.Pool`:
a representation for a *number* of *indistinguishable* resources.

As far as :py:mod:`cobald` is concerned, it is inconsequential which specific resources make up a pool.
This allows each :py:class:`~cobald.interfaces.pool.Pool` to implement its own strategy for managing resources.
For example, a :py:class:`~cobald.interfaces.pool.Pool` providing virtual machines
may silently spawn a new machine to replace another.

The purpose of a :py:class:`~cobald.interfaces.pool.Pool` is just to *provide* resources,
not use them for any specific task.
For example, the aforementioned VM may integrate into a Batch System which provides the VM with work.
What matters to :py:mod:`cobald` is only whether resources match their underlying usage.

Supply and Demand
-----------------

Each :py:class:`~cobald.interfaces.pool.Pool` effectively provides only one type of resources [#flavour]_.
The only adjustment possible from the outside is how many resources are provided.
This is expressed as :py:attr:`~cobald.interfaces.pool.Pool.supply`
and :py:attr:`~cobald.interfaces.pool.Pool.demand`:

:py:attr:`~cobald.interfaces.pool.Pool.supply` [r/o]
    The amount of resources a pool currently provides.

:py:attr:`~cobald.interfaces.pool.Pool.demand` [r/w]
    The amount of resources a pool is expected to provide.

Note that :py:attr:`~cobald.interfaces.pool.Pool.demand` is not derived by a :py:class:`~cobald.interfaces.pool.Pool`,
but should be adjusted from the outside.
The task of a :py:class:`~cobald.interfaces.pool.Pool` is only to adjust its supply to match demand.

Allocation versus Utilisation
-----------------------------

While a :py:class:`~cobald.interfaces.pool.Pool` does not calculate the demand for its resources,
it has to track and expose their usage.
This is expressed as two attributes that reflect *how much* and *how well* resources are used:

:py:attr:`~cobald.interfaces.pool.Pool.allocation` [r/o]
    Fraction of the supplied resources which are allocated for usage

:py:attr:`~cobald.interfaces.pool.Pool.utilisation` [r/o]
    Fraction of the supplied resources which are actively used

.. [#flavour] What constitutes a single "type" depends on the intended use of the resource.
              For example, it might be a generic "bytes of storage space"
              or a specific "consecutive bytes of HDD at 10 ms access time and 2500000 hrs MTBF".
