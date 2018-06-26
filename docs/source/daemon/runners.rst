====================
Concurrent Execution
====================

The :py:mod:`cobald.daemon` provides a dedicated concurrent execution environment.
This combines several execution mechanisms into a single, consistent runtime.
As a result, the daemon can consistently track the lifetime of tasks and react to failures.

The purpose of this is for components to execute concurrently,
while ensuring each component is in a valid state.
In this regard, the execution environment is similar to an init service such as systemd.

Registering Concurrent Work
---------------------------

The execution environment is exposed as :py:data:`cobald.daemon.runner`,
an instance of :py:class:`~cobald.utility.concurrent.meta_runner.MetaRunner`.
