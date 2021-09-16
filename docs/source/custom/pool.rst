=====================
Custom Pool Semantics
=====================

Adding new types of resources requires writing a new :py:class:`cobald.interfaces.Pool` implementation.
While adherence to the interface ensures compatibility,
a custom Pool must also conform to some constraints for consistency.

Behaviour of Pool Implementations
---------------------------------

The conventions on Pools are minimal, but their prevalence makes following them critical.
Basically, the conventions are implied by the semantics of a Pool's properties.

Responsiveness of Properties
    The properties :py:attr:`~cobald.interfaces.Pool.supply`, :py:attr:`~cobald.interfaces.Pool.demand`,
    :py:attr:`~cobald.interfaces.Pool.allocation`, and :py:attr:`~cobald.interfaces.Pool.utilisation`
    should respond similar to regular attributes.
    Getting and setting properties should return quickly -
    avoid lengthy computations, queries and interactions with external processes.
    Never use locking for arbitrary times.

    If you wish to represent external or complex state,
    buffer values and react to them or update them at regular intervals.

Ordering of Utilisation and Allocation
    The model of :py:attr:`~cobald.interfaces.Pool.allocation` and :py:attr:`~cobald.interfaces.Pool.utilisation`
    assumes that only allocated resources can be utilised.
    As such, :py:attr:`~cobald.interfaces.Pool.allocation`
    should generally be greater than
    :py:attr:`~cobald.interfaces.Pool.utilisation`.
    Note that this is a loose assumption that is not enforced.
    Deviations due to precision or timing should not have a significant impact.

    If you have use-cases where this assumption is not applicable, such as overbooking,
    you may want to write your own :py:class:`cobald.interfaces.Controller`.

Common Utilisation and Allocation scenarios
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Depending on the actual resources to manage, it might not be possible to accurately track
:py:attr:`~cobald.interfaces.Pool.allocation` or :py:attr:`~cobald.interfaces.Pool.utilisation`.
Furthermore, at times it is not desirable to use meaningless accuracy.
This is why :py:attr:`~cobald.interfaces.Pool.allocation` and :py:attr:`~cobald.interfaces.Pool.utilisation`
are purposely unrestrictive.
The following illustrates several scenarios how to define the two consistently.

Multi-Dimensional Allocations

.. figure:: /images/pool_allocation_cpu_ram.png
    :alt: Cobald Logo
    :height: 150
    :align: right

    Allocation of CPU and RAM
