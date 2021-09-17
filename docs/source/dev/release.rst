=======================
Versioning and Releases
=======================

The ``cobald`` versioning follows `Semantic Versioning`_.
Releases are automatically pushed to PyPI from the `GitHub COBalD repository`_.

Versioning and API stability
============================

COBalD is currently published only in the *major version zero* series.
The public API is not entirely stable, and may change between releases.
However, API changes are already kept to a minimum and
significant API changes *SHOULD* relate to an increase of the minor version.

Packages that depend on the COBalD *major version zero* series should
accept `compatible release`_ versions for minor versions.
For example, a package requiring at least ``cobald`` version ``0.12.1`` should
require ``cobald ~= 0.12.1`` to not accidentally accept ``cobald >= 0.13.0``.

Release Process
===============

There is no fixed schedule for releases;
a release is manually started whenever sufficient changes have accumulated
or a bugfix requires a prompt publication.

.. _`Semantic Versioning`: https://semver.org
.. _`GitHub COBalD repository`: https://github.com/MatterMiners/cobald
.. _`compatible release`: https://www.python.org/dev/peps/pep-0440/#compatible-release