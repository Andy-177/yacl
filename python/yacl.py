"""YACL - Yet Another Config Language (single file implementation).

A small, human readable configuration language.  This module is a
self-contained, dependency-free implementation whose API mirrors the standard
library :mod:`json` module::

    import yacl

    data = yacl.loads(text)
    text = yacl.dumps(data)

    with open("config.yacl", encoding="utf-8") as fp:
        data = yacl.load(fp)

    with open("out.yacl", "w", encoding="utf-8") as fp:
        yacl.dump(data, fp)

Usage
-----
Copy this file into your project, or put its directory on ``sys.path``::

    import sys
    sys.path.insert(0, "path/to/python")
    import yacl

The file has no third party dependencies and requires Python 3.8+.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Optional

__all__ = ["load", "loads", "dump", "dumps", "YACLDecodeError"]

__version__ = "1.0.0"


# === BEGIN PARSER ===

# ---------------------------------------------------------------------------
# Lexical helpers
# ---------------------------------------------------------------------------

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(
    r"^[+-]?(?:"
    r"\d+\.\d*|\.\d+|\d+[eE][+-]?\d+|\d+\.\d*[eE][+-]?\d+|\.\d+[eE][+-]?\d+"
    r")$"
)
_BLOCK_RE = re.compile(r"^\|\|?[0-9]*$")

_TRUE_TOKENS = frozenset(("true", "on", "enabled"))
_FALSE_TOKENS = frozenset(("false", "off", "disabled"))
_NULL_TOKENS = frozenset(("none",))

_MISSING = object()


class YACLDecodeError(ValueError):
    """Raised when YACL text cannot be parsed.

    The attributes mirror :class:`json.JSONDecodeError`: ``msg``, ``doc``,
    ``pos``, ``lineno`` and ``colno``.
    """

    def __init__(self, msg: str, doc: str = "", pos: int = 0) -> None:
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = doc.count("\n", 0, pos) + 1 if doc else 1
        self.colno = pos - doc.rfind("\n", 0, pos) if doc else 1
        super().__init__(msg)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"{self.msg}: line {self.lineno} column {self.colno} "
            f"(char {self.pos})"
        )


def _indent_of(line: str) -> int:
    """Return the number of leading whitespace characters of *line*."""
    n = 0
    for ch in line:
        if ch == " " or ch == "\t":
            n += 1
        else:
            break
    return n


def _is_dash(content: str) -> bool:
    """True if *content* starts a list item (``-`` alone or followed by space)."""
    if not content.startswith("-"):
        return False
    if len(content) == 1:
        return True
    return content[1] in " \t"


def _is_pair_line(raw: str, stripped: str) -> bool:
    """Heuristic deciding whether a line is a ``key: value`` pair.

    ``raw`` is the line content without indentation; ``stripped`` is the same
    content with comments removed.  Values that start with a quote, a
    reference or a bracket are never treated as pairs.
    """
    text = stripped.lstrip()
    if not text:
        return False
    if text[0] in "'\"[":
        return False
    return ":" in text


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class _CommentStripper:
    """Stateful removal of ``### ... ###`` comments.

    The stripper is fed the raw lines in order, together with their index.
    Lines that belong to a multi-line string or a block scalar are consumed
    directly by the parser and never reach the stripper, which keeps the state
    machine consistent.

    Removal rules:

    * ``###`` starts a multi-line comment.  When the opening ``###`` sits
      alone on its line, the comment ends at the next line that consists only
      of ``###`` at the same indentation; otherwise it ends at the next
      ``###`` wherever it appears.  This makes the mixed style used in the
      specification's example work as expected.
    * ``#`` starts a comment which ends at the end of the line, unless it is
      inside a single quoted string (or a triple quoted block, which is passed
      through untouched).
    """

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.mode = "normal"  # normal | inline_block | standalone_block
        self.end_index = -1

    def strip(self, index: int, line: str) -> str:
        if self.mode == "standalone_block":
            if index < self.end_index:
                return ""
            self.mode = "normal"
            return ""
        if self.mode == "inline_block":
            close = line.find("###")
            if close < 0:
                return ""
            self.mode = "normal"
            return self._scan(index, line, close + 3)
        return self._scan(index, line, 0)

    def _find_standalone_end(self, start: int, indent: int) -> int | None:
        for j in range(start, len(self.lines)):
            candidate = self.lines[j]
            if candidate.strip() == "###" and _indent_of(candidate) == indent:
                return j
        return None

    def _scan(self, index: int, line: str, start: int) -> str:
        out: list[str] = []
        i = start
        n = len(line)

        while i < n:
            ch = line[i]
            if ch == "#":
                if line.startswith("###", i):
                    before = line[:i]
                    after = line[i + 3 :]
                    if before.strip() == "" and after.strip() == "":
                        # Standalone opening: prefer a matching standalone
                        # closing line at the same indentation.
                        end = self._find_standalone_end(
                            index + 1, _indent_of(line)
                        )
                        if end is not None:
                            self.mode = "standalone_block"
                            self.end_index = end
                            return "".join(out)
                    # Inline comment: close at the next ### (this line or a
                    # following one).
                    close = line.find("###", i + 3)
                    if close >= 0:
                        i = close + 3
                        continue
                    self.mode = "inline_block"
                    return "".join(out)
                # Single line comment.
                return "".join(out)
            if ch == "'" or ch == '"':
                if line.startswith(ch * 3, i):
                    # Multi-line string: the rest of the line is content and is
                    # handled by the parser from the raw line.
                    out.append(line[i:])
                    return "".join(out)
                if ch == "'":
                    # Unclosed single quoted string: rest of line is literal.
                    out.append(line[i:])
                    return "".join(out)
                # Unclosed double quoted string: '#' terminates it.
                close = line.find("#", i)
                if close < 0:
                    out.append(line[i:])
                else:
                    out.append(line[i:close])
                return "".join(out)
            out.append(ch)
            i += 1
        return "".join(out)


# ---------------------------------------------------------------------------
# Reference handling
# ---------------------------------------------------------------------------


def _parse_reference(text: str) -> list[tuple[str, Any]]:
    """Split a reference expression into ``(kind, value)`` segments."""
    segments: list[tuple[str, Any]] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == ".":
            i += 1
            continue
        if ch == "[":
            j = text.find("]", i)
            if j < 0:
                j = n
            segments.append(("key", text[i + 1 : j]))
            i = j + 1
            continue
        j = i
        while j < n and text[j] not in ".[":
            j += 1
        seg = text[i:j].strip()
        i = j
        if not seg:
            continue
        if _INT_RE.match(seg):
            segments.append(("index", int(seg)))
        else:
            segments.append(("key", seg))
    return segments


def _step(current: Any, kind: str, seg: Any) -> Any:
    """Resolve one reference segment, returning ``_MISSING`` on failure."""
    if kind == "index":
        if isinstance(current, list):
            try:
                return current[seg]
            except IndexError:
                return _MISSING
        if isinstance(current, dict):
            key = str(seg)
            if key in current:
                return current[key]
            return _MISSING
        return _MISSING

    # key
    if isinstance(current, dict):
        if seg in current:
            return current[seg]
        return _MISSING
    if isinstance(current, list):
        if _INT_RE.match(seg):
            try:
                return current[int(seg)]
            except IndexError:
                return _MISSING
        return _MISSING
    return _MISSING


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class _Parser:
    def __init__(
        self,
        text: str,
        *,
        parse_float: Callable[[str], Any] = float,
        parse_int: Callable[[str], Any] = int,
        object_hook: Optional[Callable[[dict], Any]] = None,
        object_pairs_hook: Optional[Callable[[list], Any]] = None,
    ) -> None:
        self.doc = text
        if text.startswith("\ufeff"):
            text = text[1:]
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.raw_lines = text.split("\n")
        self.stripper = _CommentStripper(self.raw_lines)
        self._stripped: dict[int, str] = {}
        self.pos = 0
        self.root: Any = None
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook

    # -- low level helpers -------------------------------------------------

    def _line(self, index: int) -> str:
        cached = self._stripped.get(index)
        if cached is None:
            cached = self.stripper.strip(index, self.raw_lines[index])
            self._stripped[index] = cached
        return cached

    def _err(self, msg: str, index: int) -> YACLDecodeError:
        pos = 0
        for j in range(min(index, len(self.raw_lines))):
            pos += len(self.raw_lines[j]) + 1
        return YACLDecodeError(msg, self.doc, pos)

    def _next_content(self) -> Optional[int]:
        """Advance ``self.pos`` to the next non blank, non comment line."""
        while self.pos < len(self.raw_lines):
            stripped = self._line(self.pos)
            if stripped.strip() == "":
                self.pos += 1
                continue
            return self.pos
        return None

    def _split_pair(self, text: str, index: int) -> tuple[str, str]:
        colon = text.find(":")
        if colon < 0:
            raise self._err("expected ':' after key", index)
        return text[:colon].strip(), text[colon + 1 :]

    # -- public entry point ------------------------------------------------

    def parse(self) -> Any:
        index = self._next_content()
        if index is None:
            return None
        indent = _indent_of(self.raw_lines[index])
        raw_content = self.raw_lines[index][indent:]
        content = self._line(index)[indent:]
        if _is_dash(content):
            value = self._parse_list(indent, None)
        elif _is_pair_line(raw_content, content):
            value = self._parse_object(indent, None)
        else:
            # A document may be a single scalar value.
            self.pos = index + 1
            value = self._parse_scalar(
                raw_content, content, index, indent, None
            )
        leftover = self._next_content()
        if leftover is not None:
            raise self._err("unexpected content after document", leftover)
        if self.root is None:
            self.root = value
        return value

    # -- block level parsing ----------------------------------------------

    def _parse_block(self, indent: int, context: Any) -> Any:
        index = self._next_content()
        if index is None:
            return None
        content = self._line(index)[indent:]
        if _is_dash(content):
            return self._parse_list(indent, context)
        return self._parse_object(indent, None)

    def _parse_object(self, indent: int, first: Any) -> Any:
        obj: dict[str, Any] = {}
        if self.root is None:
            self.root = obj

        if first is not None:
            rest_raw, rest_stripped, line_index, key_indent = first
            key, raw_value = self._split_pair(rest_raw, line_index)
            if ":" in rest_stripped:
                stripped_value = rest_stripped.split(":", 1)[1]
            else:
                stripped_value = ""
            obj[key] = self._parse_pair_value(
                raw_value, stripped_value, line_index, key_indent, obj
            )

        while True:
            index = self._next_content()
            if index is None:
                break
            raw_line = self.raw_lines[index]
            line_indent = _indent_of(raw_line)
            if line_indent < indent:
                break
            if line_indent > indent:
                raise self._err("unexpected indentation", index)

            stripped = self._line(index)
            content = stripped[line_indent:]
            if _is_dash(content):
                break

            key, raw_value = self._split_pair(raw_line[line_indent:], index)
            stripped_value = content.split(":", 1)[1] if ":" in content else ""
            self.pos = index + 1
            obj[key] = self._parse_pair_value(
                raw_value, stripped_value, index, line_indent, obj
            )

        if self.object_pairs_hook is not None:
            return self.object_pairs_hook(list(obj.items()))
        if self.object_hook is not None:
            return self.object_hook(obj)
        return obj

    def _parse_list(self, indent: int, context: Any) -> list:
        result: list[Any] = []
        if self.root is None:
            self.root = result

        while True:
            index = self._next_content()
            if index is None:
                break
            raw_line = self.raw_lines[index]
            line_indent = _indent_of(raw_line)
            if line_indent < indent:
                break
            if line_indent > indent:
                raise self._err("unexpected indentation", index)

            stripped = self._line(index)
            content = stripped[line_indent:]
            if not _is_dash(content):
                break

            after_raw = raw_line[line_indent + 1 :]
            k = 0
            while k < len(after_raw) and after_raw[k] in " \t":
                k += 1
            rest_raw = after_raw[k:]
            if len(content) > 1 + k:
                rest_stripped = content[1 + k :]
            else:
                rest_stripped = ""
            key_indent = line_indent + 1 + k
            self.pos = index + 1

            if rest_stripped.strip() == "":
                # ``-`` alone: the item is defined by the deeper block.
                nxt = self._next_content()
                if nxt is not None and _indent_of(self.raw_lines[nxt]) > indent:
                    result.append(
                        self._parse_block(_indent_of(self.raw_lines[nxt]), context)
                    )
                else:
                    result.append(None)
            elif _is_pair_line(rest_raw, rest_stripped):
                result.append(
                    self._parse_object(
                        key_indent, (rest_raw, rest_stripped, index, key_indent)
                    )
                )
            else:
                result.append(
                    self._parse_scalar(
                        rest_raw, rest_stripped, index, line_indent, context
                    )
                )
        return result

    # -- value level parsing ----------------------------------------------

    def _parse_pair_value(
        self,
        raw_value: str,
        stripped_value: str,
        line_index: int,
        key_indent: int,
        context: Any,
    ) -> Any:
        if stripped_value.lstrip() == "":
            # No inline value: a deeper block (if any) becomes the value.
            nxt = self._next_content()
            if nxt is not None and _indent_of(self.raw_lines[nxt]) > key_indent:
                return self._parse_block(
                    _indent_of(self.raw_lines[nxt]), context
                )
            return None
        return self._parse_scalar(
            raw_value, stripped_value, line_index, key_indent, context
        )

    def _parse_scalar(
        self,
        raw_value: str,
        stripped_value: str,
        line_index: int,
        key_indent: int,
        context: Any,
    ) -> Any:
        raw = raw_value.lstrip()
        token = stripped_value.strip()

        # Multi-line strings ------------------------------------------------
        if raw.startswith("'''"):
            return self._parse_triple(raw, "'''", line_index, False)
        if raw.startswith('"""'):
            return self._parse_triple(raw, '"""', line_index, True)

        # Single line strings ----------------------------------------------
        if raw.startswith("'"):
            # Unclosed: everything to the end of the line is literal.
            return raw[1:]
        if raw.startswith('"'):
            # '#' terminates the string.
            end = raw.find("#", 1)
            text = raw[1:] if end < 0 else raw[1:end]
            return text.rstrip()

        # Block scalars -----------------------------------------------------
        if _BLOCK_RE.match(token):
            return self._parse_block_scalar(token, line_index, key_indent)

        # Inline empty collections (extension for round tripping) ----------
        if token == "{}":
            return {}
        if token == "[]":
            return []

        # References --------------------------------------------------------
        if raw.startswith("["):
            return self._resolve_reference(token, context)

        # Scalars -----------------------------------------------------------
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
        if token in _NULL_TOKENS:
            return None
        if _INT_RE.match(token):
            return self.parse_int(token)
        if _FLOAT_RE.match(token):
            return self.parse_float(token)

        # Bare string fallback.
        return token

    def _parse_triple(
        self, first_part: str, delimiter: str, line_index: int, remove_hash: bool
    ) -> str:
        rest = first_part[3:]
        close = rest.find(delimiter)
        lines: list[str] = []
        if close >= 0:
            lines.append(rest[:close])
            self.pos = line_index + 1
        else:
            lines.append(rest)
            i = line_index + 1
            closed = False
            while i < len(self.raw_lines):
                line = self.raw_lines[i]
                close = line.find(delimiter)
                if close >= 0:
                    lines.append(line[:close])
                    i += 1
                    closed = True
                    break
                lines.append(line)
                i += 1
            if not closed:
                raise self._err("unterminated multi-line string", line_index)
            self.pos = i

        if remove_hash:
            lines = [line.split("#", 1)[0] for line in lines]

        content = "\n".join(lines)
        # Trim exactly one leading and one trailing newline.
        if content.startswith("\n"):
            content = content[1:]
        if content.endswith("\n"):
            content = content[:-1]
        return content

    def _parse_block_scalar(
        self, header: str, line_index: int, key_indent: int
    ) -> str:
        remove_hash = header.startswith("||")
        count = header[2:] if remove_hash else header[1:]
        self.pos = line_index + 1

        if count:
            wanted = int(count)
            out: list[str] = []
            base: Optional[int] = None
            for _ in range(wanted):
                if self.pos >= len(self.raw_lines):
                    break
                line = self.raw_lines[self.pos]
                if line.strip():
                    line_indent = _indent_of(line)
                    if base is None:
                        base = line_indent
                    elif line_indent < base:
                        break
                if remove_hash:
                    line = line.split("#", 1)[0]
                out.append(line)
                self.pos += 1
            return "\n".join(out)

        # Indentation driven mode.
        lines: list[str] = []
        while self.pos < len(self.raw_lines):
            line = self.raw_lines[self.pos]
            if line.strip() == "":
                lines.append(line)
                self.pos += 1
                continue
            if _indent_of(line) <= key_indent:
                break
            lines.append(line)
            self.pos += 1

        non_blank = [line for line in lines if line.strip() != ""]
        if not non_blank:
            return ""
        # Blank lines inside the block are preserved, but trailing blank lines
        # (which separate the block from the next key) are not part of it.
        while lines and lines[-1].strip() == "":
            lines.pop()
        common = min(_indent_of(line) for line in non_blank)

        out = []
        for line in lines:
            if line.strip() == "":
                out.append("")
            else:
                out.append(line[common:])
        if remove_hash:
            out = [line.split("#", 1)[0] for line in out]
        return "\n".join(out)

    def _resolve_reference(self, text: str, context: Any) -> Any:
        segments = _parse_reference(text)
        if not segments:
            return None
        current = context if context is not None else self.root
        first = True
        for kind, seg in segments:
            value = _step(current, kind, seg)
            if value is _MISSING:
                if (
                    first
                    and context is not None
                    and context is not self.root
                ):
                    value = _step(self.root, kind, seg)
                if value is _MISSING:
                    return None
            current = value
            first = False
        return current


# ---------------------------------------------------------------------------
# Public API: deserialization
# ---------------------------------------------------------------------------


def loads(
    s: str | bytes | bytearray,
    *,
    parse_float: Callable[[str], Any] = float,
    parse_int: Callable[[str], Any] = int,
    object_hook: Optional[Callable[[dict], Any]] = None,
    object_pairs_hook: Optional[Callable[[list], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Deserialize *s* (a YACL document) to a Python object.

    The signature mirrors :func:`json.loads`.  Unknown keyword arguments are
    accepted and ignored for compatibility.
    """
    if isinstance(s, (bytes, bytearray)):
        s = bytes(s).decode("utf-8")
    if not isinstance(s, str):
        raise TypeError(
            "the YACL document must be str, bytes or bytearray, "
            f"not {type(s).__name__}"
        )
    return _Parser(
        s,
        parse_float=parse_float,
        parse_int=parse_int,
        object_hook=object_hook,
        object_pairs_hook=object_pairs_hook,
    ).parse()


def load(
    fp: Any,
    *,
    parse_float: Callable[[str], Any] = float,
    parse_int: Callable[[str], Any] = int,
    object_hook: Optional[Callable[[dict], Any]] = None,
    object_pairs_hook: Optional[Callable[[list], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Deserialize a YACL document from a file-like object.

    The signature mirrors :func:`json.load`.
    """
    return loads(
        fp.read(),
        parse_float=parse_float,
        parse_int=parse_int,
        object_hook=object_hook,
        object_pairs_hook=object_pairs_hook,
        **kwargs,
    )


# === END PARSER ===

# === BEGIN DUMPER ===

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


# === END DUMPER ===