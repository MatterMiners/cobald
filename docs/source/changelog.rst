.. Created by change-log.py at 2019-09-03, command
   './dev_tools/change-log.py docs/source/changes/ compile -o ./docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'

#########
CHANGELOG
#########

[0.10.0] - 2019-09-03
=====================

Added
-----

* Pools can be templated via ``.s`` in Python configuration files
* YAML configuration files support plugins via ``!MyPlugin`` tags
* the ``cobald`` namespace allows for external plugin packages

Fixed
-----

* fixed Line Protocol sending illegal content

Security
--------

* YAML configuration files no longer allow arbitrary ``!!python/object`` tags

