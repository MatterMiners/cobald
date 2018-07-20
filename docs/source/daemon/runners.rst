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

.. code:: python

    @service(flavour=threading)
    class MyService(object):
        # will be executed in a thread once the daemon starts
        def run():
            ...

Triggering Background Tasks
---------------------------

The execution environment is exposed as :py:data:`cobald.daemon.runtime`,
an instance of :py:class:`~cobald.daemon.service.ServiceRunner`.
