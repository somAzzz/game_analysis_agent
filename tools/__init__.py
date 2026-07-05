"""Make ``tools/`` importable as a package so tests can patch submodules.

The CLI scripts in this directory remain runnable as ``python3 tools/...``
because they each insert ``src/`` onto ``sys.path`` themselves; this
``__init__.py`` only exists to enable import-by-name from the test
harness and from any future entry-point that wants to drive the same
functions programmatically.
"""