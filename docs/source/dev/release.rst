=======================
Versioning and Releases
=======================

The COBalD versioning follows `Semantic Versioning`_.
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
a release is manually started whenever significant changes have accumulated
or a bugfix requires a prompt publication.

.. note::

    The following section is only relevant for maintainers of COBalD.

Releases are automatically published to PyPI when a GitHub release is created.
Each release should be prepared and reviewed via a pull request.

1. Create a new branch ``releases/v<version>`` and pull request
    * Add all to-be-released pull requests to the description

2. Review all changes added by the new release
    * Ensure naming, unittests and docs are appropriate

3. Merge new version metadata (e.g. v3.9.2) to repository
    * Fix change fragment version via ``change log … release v3.9.2``
    * Adjust and commit ``__version__ = "3.9.2"`` in ``cobald.__about__``
    * Create a git tag such as ``git tag -a "v3.9.2" -m "important changes"``

Once the pull request has been reviewed and merged, create a new `GitHub release`_.

.. _`Semantic Versioning`: https://semver.org
.. _`GitHub COBalD repository`: https://github.com/MatterMiners/cobald
.. _`compatible release`: https://www.python.org/dev/peps/pep-0440/#compatible-release
.. _`GitHub release`: https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository