.. Created by log.py at 2020-02-24, command
   '/Users/mfischer/PycharmProjects/cobald/venv/lib/python3.7/site-packages/change/__main__.py log docs/source/changes compile --output docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'
#########
ChangeLog
#########

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

