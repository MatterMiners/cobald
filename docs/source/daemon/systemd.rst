===============
systemd Configs
===============

You can run :py:mod:`cobald` as a system service.
We provide systemd configs for multiple :py:mod:`cobald` instances run as services.
You can manage several instances which are identified with a systemd instance name.

Create a file named  ``cobald@.service`` into the ``/usr/lib/systemd/system`` directory.

An example of an systemd config file:

.. literalinclude:: cobald@.service

In this example, the configs for the different COBalD instances are located at ``/etc/cobald/instance-name.py``.
Please ensure that the choosen python interpreter has :py:mod:`cobald` installed!

After you created or changed the file you need to run:

.. code:: bash

    $ systemctl daemon-reload


Now you can manage the :py:mod:`cobald` instance which loads the ``/etc/cobald/instance-name.py`` config file.


 - start one instance of :py:mod:`cobald`

    .. code-block:: bash

        $ systemctl start cobald@instance-name

 -  stop the instance of :py:mod:`cobald`

    .. code-block:: bash

        $ systemctl stop cobald@instance-name

 -  report the current status of the :py:mod:`cobald` instance

    .. code-block:: bash

        $ systemctl status cobald@instance-name

 -  :py:mod:`cobald` instance starts at system boot

    .. code:: bash

        $ systemctl enable cobald@instance-name

