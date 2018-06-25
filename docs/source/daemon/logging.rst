===========================
Standard Logging Facilities
===========================

The :py:mod:`cobald.daemon` provides several separate :py:mod:`logging` channels.
Each exposes information from a different view and for a different audience.
Both core components and plugins should hook into these channels to supply appropriate information.

Logging Channels
################

Channels are separated by a hierarchical :py:mod:`logging` name.

``"cobald.runtime"``
    Diagnostic information on the health of the daemon and its abstractions.
    This includes resources initialised (e.g. databases or modules),
    and any failures that may affect daemon stability (e.g. unavailable resources).

``"cobald.control"``
    Information specific to the pool control model.
    This includes decisions made and statistics used for this purpose.

``"cobald.monitor"``
    Monitoring information for automated processing.

Log providers hook into channels by creating a sub-logger.
For example, the daemon core uses the ``"cobald.runtime.daemon"`` logger for diagnostics.

The Monitor Channel
-------------------

In contrast to other channels, the ``"cobald.monitor"`` channel provides structured data.
This data is suitable for data transfer formats such as JSON or telegraf.
Each entry consists of an identifier and a dictionary of data:

.. code:: python

    # get a separate logger in the 'cobald.monitor' channel
    logger = logging.getLogger('cobald.monitor.wheatherapi')
    # message and args forms the identifier, `extras` contains data
    logger.info('forecast.%s', location, extras={'temperature': 298, 'humidity': 0.45})
