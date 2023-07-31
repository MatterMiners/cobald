.. Created by log.py at 2023-07-26, command
   '/Users/mfischer/PycharmProjects/cobald/venv/lib/python3.9/site-packages/change/__main__.py log docs/source/changes compile -o docs/source/changelog.rst --categories Added Changed Fixed Security Deprecated'
   based on the format of 'https://keepachangelog.com/'
#########
ChangeLog
#########

0.14 Series
===========

Version [0.14.0] - 2023-07-26
+++++++++++++++++++++++++++++

* **[Deprecated]** Minimal Python version is 3.8

0.13 Series
===========

Version [0.13.0] - 2022-08-16
+++++++++++++++++++++++++++++

* **[Changed]** Configuration is processed after daemon and `asyncio` initialisation
* **[Changed]** Daemon core implementation is based on `asyncio`

0.12 Series
===========

Version [0.12.3] - 2021-10-29
+++++++++++++++++++++++++++++

* **[Added]** YAML ``!tags`` may be eagerly evaluated

Version [0.12.2] - 2021-09-15
+++++++++++++++++++++++++++++

* **[Fixed]** pipeline configuration may combine ``__type__`` and ``!yaml`` style
* **[Fixed]** pipeline configuration no longer suppresses ``TypeError``

Version [0.12.1] - 2020-04-15
+++++++++++++++++++++++++++++

* **[Fixed]** fallback for fitness of WeightedComposite depends on supply

Version [0.12.0] - 2020-02-26
+++++++++++++++++++++++++++++

* **[Changed]** Section Plugin settings are now specified via decorators

0.11 Series
===========

Version [0.11.0] - 2020-02-24
+++++++++++++++++++++++++++++

* **[Changed]** COBalD configuration files may include additional sections

0.10 Series
===========

Version [0.10.0] - 2019-09-03
+++++++++++++++++++++++++++++

* **[Added]** Pools can be templated via ``.s`` in Python configuration files
* **[Added]** YAML configuration files support plugins via ``!MyPlugin`` tags
* **[Added]** the ``cobald`` namespace allows for external plugin packages

* **[Fixed]** fixed Line Protocol sending illegal content

* **[Security]** YAML configuration files no longer allow arbitrary ``!!python/object`` tags

