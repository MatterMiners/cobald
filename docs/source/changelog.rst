.. Created by change-log.py at 2019-08-15, command
   './dev_tools/change-log.py docs/source/changes/ compile -o ./docs/source/changelog.rst'

#########
CHANGELOG
#########

[Unreleased] - 2019-08-15
=========================

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

