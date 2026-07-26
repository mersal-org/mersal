Contributing
=============

Development setup
------------------

Mersal uses `uv <https://docs.astral.sh/uv/>`_ for dependency management and
`mise <https://mise.jdx.dev/>`_ to run project tasks.

.. code-block:: shell

   mise run install    # create the venv, install deps, install pre-commit hooks
   mise run test        # run the test suite
   mise run lint        # format + run pre-commit
   mise run type-check   # ty + basedpyright + mypy
   mise run docs:serve   # live-reloading docs server

Run ``mise tasks`` to see everything available.

Versioning
----------

Mersal follows `Semantic Versioning <https://semver.org/>`_.

The version number is **never** hand-edited in ``pyproject.toml``. It is
derived entirely from git tags via `hatch-vcs
<https://github.com/ofek/hatch-vcs>`_:

- On a commit that is exactly a tag (e.g. ``v1.2.3``), the package version is
  ``1.2.3``.
- On any other commit, the version is a development version derived from the
  most recent tag, e.g. ``1.2.4.dev3`` for the 3rd commit after ``v1.2.3``.

This means making a release is just a matter of pushing a tag -- there is no
version-bump commit or changelog-file merge conflict to manage.

Making a release
-----------------

1. Make sure ``main`` is green (CI passing) and contains everything you want
   to ship.
2. Decide the next version per SemVer:

   - **patch** (``1.2.3`` -> ``1.2.4``): bug fixes only, no API changes.
   - **minor** (``1.2.3`` -> ``1.3.0``): new, backwards-compatible functionality.
   - **major** (``1.2.3`` -> ``2.0.0``): breaking changes.

3. Tag the release and push the tag:

   .. code-block:: shell

      git tag v1.2.4
      git push origin v1.2.4

4. Go to `GitHub Releases
   <https://github.com/mersal-org/mersal/releases/new>`_, pick the tag you
   just pushed, click **Generate release notes** (GitHub builds these from
   merged PR titles -- keep PR titles/commits following `Conventional
   Commits <https://www.conventionalcommits.org/>`_, which is already
   enforced by pre-commit), review, and click **Publish release**.

5. Publishing the release triggers `.github/workflows/publish.yml
   <.github/workflows/publish.yml>`_, which builds the package with the
   version baked in from the tag and uploads it to PyPI using `Trusted
   Publishing <https://docs.pypi.org/trusted-publishers/>`_ -- no API tokens
   involved.

Continuous pre-releases on Test PyPI
-------------------------------------

Every push to ``main`` (i.e. every merged PR) automatically builds the
package and uploads it to `Test PyPI
<https://test.pypi.org/project/mersal/>`_ under its dev version
(e.g. ``1.2.4.dev3``). This lets you or early adopters install and sanity
check the very latest ``main`` before it's ever cut into a real release:

.. code-block:: shell

   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mersal

This mirrors the workflow used by projects like `structlog
<https://github.com/hynek/structlog/blob/main/.github/workflows/pypi-package.yml>`_.
