====================
Concurrent Execution
====================

The :py:mod:`cobald.daemon` provides a dedicated concurrent execution environment.
This combines several execution mechanisms into a single, consistent runtime.
As a result, the daemon can consistently track the lifetime of tasks and react to failures.

The purpose of this is for components to execute concurrently,
while ensuring each component is in a valid state.
In this regard, the execution environment is similar to an init service such as systemd.

Registering Background Services
-------------------------------

The primary entry point to the runtime is defining services:
the main threads of service instances are automatically started, tracked and handled by the :py:mod:`cobald.daemon`.
This allows services to update information, manage resources and react to changing conditions.

A service is defined by applying the :py:func:`~cobald.daemon.service.service` decorator to a class.
This automatically schedules the ``run`` method of any instances for execution as a background task.

.. code:: python

    @service(flavour=threading)
    class MyService(object):
        # run method of any instances is executed in a thread once the daemon starts
        def run():
            ...

Task Execution and Abortion
---------------------------

Any background task is adopted by the daemon runtime.
Adopted tasks are executed separately for each flavour;
this means that ``async`` code of the same flavour is never run in parallel.
However, tasks of non-``async`` flavour, such as ``threading``, and different flavours can be run in parallel.

Any adopted tasks are considered self-contained by the runtime.
Most importantly, they have no parent that can receive return values or exceptions.

.. warning:: Any unhandled return values and exceptions are considered an error.
             The daemon automatically terminates in this case.

On termination, the daemon aborts all remaining background tasks.
Whether this is graceful or not depends on the flavour of each task.
In general, coroutines are gracefully terminated whereas subroutines are not.

Triggering Background Tasks
---------------------------

The execution environment is exposed as :py:data:`cobald.daemon.runtime`,
an instance of :py:class:`~cobald.daemon.service.ServiceRunner`.
Via this entry point, new tasks may be launched after the daemon has started.

.. describe:: runtime.adopt(payload, *args, flavour, **kwargs)

    Run a ``payload`` of the appropriate ``flavour`` in the background.
    The caller is not blocked, but cannot receive any return value or exceptions.

    .. note:: It is a fatal error if ``payload`` produces any value or exception.

.. describe:: runtime.execute(payload, *args, flavour, **kwargs)

    Run a ``payload`` of the appropriate ``flavour`` until completion.
    The caller is blocked during execution, and receives any return value or exceptions.

If ``*args`` or ``**kwargs`` are provided, the ``payload`` is run as ``payload(*args, **kwargs)``.

Available Flavours
------------------

Flavours are identified by the underlying module.
The following types are currently supported:

``asnycio``

    Coroutines implemented with the :py:mod:`asyncio` library.
    Payloads are gracefully cancelled.

``trio``

    Coroutines implemented with the :py:mod:`trio` library.
    Payloads are gracefully cancelled.

``threading``

    Subroutines implemented with the :py:mod:`threading` library.
    Payloads run as daemons and ungracefully terminated.
