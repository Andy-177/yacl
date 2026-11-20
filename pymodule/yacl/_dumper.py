"""Serializer implementation for the YACL configuration language."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional

__all__ = ["dumps", "dump"]

# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


class _Dumper:
    def __init__(
        self,
        *,
        indent: Any,
        sort_keys: bool,
        default: Optional[Callable[[Any], Any]],
        allow_nan: bool,
        check_circular: bool,
        skipkeys: bool,
    ) -> None:
        if indent is None:
            self.unit = "    "
        elif isinstance(indent, int):
            self.unit = " " * max(0, indent)
        else:
            self.unit = str(indent)
        self.sort_keys = sort_keys
        self.default = default
        self.allow_nan = allow_nan
        self.check_circular = check_circular
        self.skipkeys = skipkeys
        self._seen: set[int] = set()

    # -- helpers -----------------------------------------------------------

    def _check(self, obj: Any) -> None:
        if not self.check_circular:
            return
        if isinstance(obj, (dict, list, tuple)):
            marker = id(obj)
            if marker in self._seen:
                raise ValueError("Circular reference detected")
            self._seen.add(marker)

    def _uncheck(self, obj: Any) -> None:
        if self.check_circular and isinstance(obj, (dict, list, tuple)):
            self._seen.discard(id(obj))

    def _items(self, obj: dict) -> list[tuple[str, Any]]:
        items = list(obj.items())
        if self.sort_keys:
            items.sort(key=lambda kv: str(kv[0]))
        return items

    def _normalize(self, value: Any) -> Any:
        """Apply the ``default`` hook until *value* is a basic type."""
        while value is not None and not isinstance(
            value, (dict, list, tuple, str, int, float, bool)
        ):
            if self.default is None:
                raise TypeError(
                    f"Object of type {type(value).__name__} is not YACL "
                    "serializable"
                )
            value = self.default(value)
        return value

    def _scalar(self, value: Any) -> str:
        if value is None:
            return "none"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                if not self.allow_nan:
                    raise ValueError("Out of range float values are not YACL compliant")
                if math.isnan(value):
                    return "nan"
                return "inf" if value > 0 else "-inf"
            return repr(value)
        if isinstance(value, str):
            return "'" + value
        if self.default is not None:
            return self._scalar(self.default(value))
        raise TypeError(
            f"Object of type {type(value).__name__} is not YACL serializable"
        )

    def _emit_string(
        self,
        value: str,
        head: str,
        key_col: int,
        out: list[str],
    ) -> None:
        """Emit a string value whose first line starts after *head*."""
        has_newline = "\n" in value or "\r" in value
        if not has_newline:
            if value.startswith("'''"):
                # Would be mistaken for a triple quoted string; use a block.
                self._emit_string_block(value, head, key_col, out)
            else:
                out.append(head + "'" + value)
            return
        if "'''" not in value:
            # Triple single quotes preserve everything except one leading and
            # one trailing newline, which we account for by adding them back.
            out.append(head + "'''")
            out.extend(value.split("\n"))
            out.append("'''")
        else:
            self._emit_string_block(value, head, key_col, out)

    def _emit_string_block(
        self, value: str, head: str, key_col: int, out: list[str]
    ) -> None:
        out.append(head + "|")
        pad = " " * (key_col + len(self.unit))
        for line in value.split("\n"):
            out.append(pad + line if line else "")

    # -- emission ----------------------------------------------------------

    def _emit_pair(
        self, prefix: str, key: str, value: Any, key_col: int, out: list[str]
    ) -> None:
        value = self._normalize(value)
        head = prefix + key + ":"
        if isinstance(value, dict):
            if not value:
                out.append(head + " {}")
                return
            self._check(value)
            out.append(head)
            self._emit_dict(value, key_col + len(self.unit), out)
            self._uncheck(value)
        elif isinstance(value, (list, tuple)):
            if not value:
                out.append(head + " []")
                return
            self._check(value)
            out.append(head)
            self._emit_list(value, key_col + len(self.unit), out)
            self._uncheck(value)
        elif isinstance(value, str):
            self._emit_string(value, head + " ", key_col, out)
        else:
            out.append(head + " " + self._scalar(value))

    def _emit_dict(self, obj: dict, level: int, out: list[str]) -> None:
        for key, value in self._items(obj):
            if not isinstance(key, str):
                if self.skipkeys and not isinstance(
                    key, (str, int, float, bool, type(None))
                ):
                    continue
                key = str(key)
            self._emit_pair(" " * level, key, value, level, out)

    def _emit_list(self, lst: list, level: int, out: list[str]) -> None:
        pad = " " * level
        for item in lst:
            item = self._normalize(item)
            if isinstance(item, dict):
                if not item:
                    out.append(pad + "- {}")
                    continue
                self._check(item)
                items = self._items(item)
                first_key, first_value = items[0]
                self._emit_pair(
                    pad + "- ", first_key, first_value, level + 2, out
                )
                for key, value in items[1:]:
                    self._emit_pair(" " * (level + 2), key, value, level + 2, out)
                self._uncheck(item)
            elif isinstance(item, (list, tuple)):
                if not item:
                    out.append(pad + "- []")
                    continue
                self._check(item)
                out.append(pad + "-")
                self._emit_list(item, level + len(self.unit), out)
                self._uncheck(item)
            elif isinstance(item, str):
                self._emit_string(item, pad + "- ", level, out)
            else:
                out.append(pad + "- " + self._scalar(item))

    # -- entry point -------------------------------------------------------

    def encode(self, obj: Any) -> str:
        obj = self._normalize(obj)
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            out: list[str] = []
            self._check(obj)
            self._emit_dict(obj, 0, out)
            self._uncheck(obj)
            return "\n".join(out)
        if isinstance(obj, (list, tuple)):
            if not obj:
                return "[]"
            out = []
            self._check(obj)
            self._emit_list(obj, 0, out)
            self._uncheck(obj)
            return "\n".join(out)
        if isinstance(obj, str):
            out = []
            self._emit_string(obj, "", 0, out)
            return "\n".join(out)
        return self._scalar(obj)


def dumps(
    obj: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    default: Optional[Callable[[Any], Any]] = None,
    indent: Any = 4,
    sort_keys: bool = False,
    **kwargs: Any,
) -> str:
    """Serialize *obj* to a YACL formatted string.

    The signature mirrors :func:`json.dumps`.  ``ensure_ascii`` is accepted for
    compatibility but has no effect: YACL strings are literal text and are
    always written as UTF-8 (the language has no escape sequences).
    """
    dumper = _Dumper(
        indent=indent,
        sort_keys=sort_keys,
        default=default,
        allow_nan=allow_nan,
        check_circular=check_circular,
        skipkeys=skipkeys,
    )
    return dumper.encode(obj)


def dump(
    obj: Any,
    fp: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    default: Optional[Callable[[Any], Any]] = None,
    indent: Any = 4,
    sort_keys: bool = False,
    **kwargs: Any,
) -> None:
    """Serialize *obj* as a YACL formatted stream to *fp*.

    The signature mirrors :func:`json.dump`.
    """
    fp.write(
        dumps(
            obj,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            indent=indent,
            sort_keys=sort_keys,
            **kwargs,
        )
    )
