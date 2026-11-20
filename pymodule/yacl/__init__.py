"""YACL - Yet Another Config Language.

A lightweight, human readable configuration language.  This package is
generated from the single file implementation in ``python/yacl.py`` by
``sync.py``; edit that file and re-run the sync script.

The API mirrors the standard library :mod:`json` module::

    import yacl

    data = yacl.loads(text)
    text = yacl.dumps(data)
"""

from ._dumper import dump, dumps
from ._parser import YACLDecodeError, load, loads

__all__ = ["load", "loads", "dump", "dumps", "YACLDecodeError"]

__version__ = "1.0.0"
