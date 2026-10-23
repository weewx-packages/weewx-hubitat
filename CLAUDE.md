# weewx-hubitat

WeeWX RESTful service that posts loop packets as JSON to the WeeWX device driver on a Hubitat hub. Runtime module `bin/user/hubitat.py`, installer `install.py` (name `hubitat`). Independent continuation of dennypage/weewx-hubitat, see `ORIGIN.md`. Nothing is mirrored into this repository. The Hubitat driver lives in dennypage/hubitat and is linked, not copied.

Python 3 only, WeeWX 5.x. Style of the file: no runtime annotations, types in Google-style docstrings. The BSD-2-Clause grant is in the header of `bin/user/hubitat.py` and in `LICENSE`; keep both. Date changes to source files (note in the header) and add a `changelog` entry.

Version lives in `install.py` and `VERSION` in the module. A test checks that they agree. README follows the weewx-packages schema and names no versions or archive URLs; installation links to the catalog page.

## Phase

Alpha. A few fast smoke tests, no edge-case suite.

## Tests

`python -m pytest -q tests` in an environment with WeeWX and pytest, about 2 s. The tests use a local `http.server` and a temporary station directory, no network and no hub.
