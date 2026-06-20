"""
yacl - Yet Another Config Language (YACL) Parser
"""

import re
from typing import Any, Dict, List, Union, Optional, TextIO


class YACLParseError(Exception):
    def __init__(self, message: str, line: int = None, col: int = None):
        self.line = line
        self.col = col
        msg = f"YACL parse error"
        if line is not None:
            msg += f" at line {line}"
        if col is not None:
            msg += f", column {col}"
        msg += f": {message}"
        super().__init__(msg)


class _Parser:
    TRUE_VALUES = {'true', 'on', 'enabled', 'yes'}
    FALSE_VALUES = {'false', 'off', 'disabled', 'no'}

    def __init__(self):
        self.lines = []
        self.index = 0

    def parse(self, text: str) -> Any:
        self.lines = text.splitlines()
        self.index = 0
        self._skip_empty_lines()
        if self.index >= len(self.lines):
            return None
        result = self._parse_block(0)
        return result if result is not None else {}

    def _skip_empty_lines(self):
        while self.index < len(self.lines) and self.lines[self.index].strip() == '':
            self.index += 1

    def _get_indent(self, line: str) -> int:
        return len(line) - len(line.lstrip(' '))

    def _parse_block(self, indent_level: int) -> Dict[str, Any]:
        obj = {}
        while self.index < len(self.lines):
            self._skip_empty_lines()
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            indent = self._get_indent(line)
            if indent < indent_level:
                break
            stripped = line.lstrip()
            if stripped.startswith('###'):
                self.index += 1
                while self.index < len(self.lines):
                    if self.lines[self.index].lstrip().startswith('###'):
                        self.index += 1
                        break
                    self.index += 1
                continue
            if stripped.startswith('#'):
                self.index += 1
                continue
            if stripped.startswith('-'):
                break
            colon_pos = stripped.find(':')
            if colon_pos == -1:
                self.index += 1
                continue
            key = stripped[:colon_pos].strip()
            if not key:
                self.index += 1
                continue
            if '[' in key or ']' in key:
                raise YACLParseError(f"Invalid key '{key}': keys cannot contain '[' or ']'")
            rest_after_colon = stripped[colon_pos+1:]
            if rest_after_colon and rest_after_colon[0] not in (' ', '\t'):
                raise YACLParseError(f"Invalid syntax: colon must be followed by space or end of line, got '{line}'")
            value_part = stripped[colon_pos+1:].lstrip()
            self.index += 1  # consume current line
            if value_part:
                if value_part.startswith("'''") and "'''" not in value_part[3:]:
                    prefix = value_part[3:]
                    value = self._read_multiline_string(0, prefix=prefix, quote="'''")[0]
                    obj[key] = value
                elif value_part.startswith('"""') and '"""' not in value_part[3:]:
                    prefix = value_part[3:]
                    value = self._read_multiline_string(0, prefix=prefix, quote='"""')[0]
                    obj[key] = value
                else:
                    obj[key] = self._parse_inline_value(value_part, indent + 2)
            else:
                self._skip_empty_lines()
                if self.index >= len(self.lines):
                    obj[key] = None
                    break
                next_line = self.lines[self.index]
                next_indent = self._get_indent(next_line)
                if next_indent > indent:
                    next_stripped = next_line.lstrip()
                    if next_stripped.startswith('-'):
                        obj[key] = self._parse_list(indent + 2)
                    elif next_stripped.startswith("'''") or next_stripped.startswith('"""'):
                        value = self._read_multiline_string(indent + 2)[0]
                        obj[key] = value
                    else:
                        obj[key] = self._parse_block(indent + 2)
                else:
                    obj[key] = None
        return obj

    def _parse_list(self, indent_level: int) -> List[Any]:
        items = []
        while self.index < len(self.lines):
            self._skip_empty_lines()
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            indent = self._get_indent(line)
            if indent < indent_level:
                break
            stripped = line.lstrip()
            if stripped.startswith('###'):
                self.index += 1
                while self.index < len(self.lines):
                    if self.lines[self.index].lstrip().startswith('###'):
                        self.index += 1
                        break
                    self.index += 1
                continue
            if stripped.startswith('#'):
                self.index += 1
                continue
            if not stripped.startswith('-'):
                break
            rest = stripped[1:].lstrip()
            self.index += 1
            if rest == '':
                self._skip_empty_lines()
                if self.index >= len(self.lines):
                    items.append(None)
                    continue
                next_line = self.lines[self.index]
                next_indent = self._get_indent(next_line)
                if next_indent > indent_level:
                    next_stripped = next_line.lstrip()
                    if next_stripped.startswith('-'):
                        items.append(self._parse_list(indent_level + 2))
                    elif next_stripped.startswith("'''") or next_stripped.startswith('"""'):
                        value = self._read_multiline_string(indent_level)[0]
                        items.append(value)
                    else:
                        items.append(self._parse_block(indent_level + 2))
                else:
                    items.append(None)
                continue
            if ':' in rest and not rest.strip().startswith('#'):
                colon_pos = rest.find(':')
                key = rest[:colon_pos].strip()
                val_part = rest[colon_pos+1:].lstrip()
                if val_part:
                    value = self._parse_inline_value(val_part, indent + 2)
                    d = {key: value}
                    items.append(d)
                    key_indent = indent + 2
                    while self.index < len(self.lines):
                        line = self.lines[self.index]
                        line_indent = self._get_indent(line)
                        if line_indent != key_indent:
                            break
                        stripped = line.lstrip()
                        if stripped.startswith('#') or stripped.startswith('-'):
                            break
                        colon_pos = stripped.find(':')
                        if colon_pos == -1:
                            break
                        sub_key = stripped[:colon_pos].strip()
                        sub_val_part = stripped[colon_pos+1:].lstrip()
                        self.index += 1
                        if sub_val_part:
                            d[sub_key] = self._parse_inline_value(sub_val_part, line_indent + 2)
                        else:
                            self._skip_empty_lines()
                            if self.index < len(self.lines):
                                next_line = self.lines[self.index]
                                next_indent2 = self._get_indent(next_line)
                                if next_indent2 > line_indent:
                                    next_stripped2 = next_line.lstrip()
                                    if next_stripped2.startswith('-'):
                                        d[sub_key] = self._parse_list(line_indent + 2)
                                    elif next_stripped2.startswith("'''") or next_stripped2.startswith('"""'):
                                        d[sub_key] = self._read_multiline_string(line_indent + 2)[0]
                                    else:
                                        d[sub_key] = self._parse_block(line_indent + 2)
                                else:
                                    d[sub_key] = None
                            else:
                                d[sub_key] = None
                else:
                    self._skip_empty_lines()
                    if self.index >= len(self.lines):
                        items.append({key: None})
                        break
                    next_line = self.lines[self.index]
                    next_indent = self._get_indent(next_line)
                    if next_indent > indent + 2:
                        next_stripped = next_line.lstrip()
                        if next_stripped.startswith('-'):
                            value = self._parse_list(indent + 2)
                        elif next_stripped.startswith("'''") or next_stripped.startswith('"""'):
                            value = self._read_multiline_string(indent + 2)[0]
                        else:
                            value = self._parse_block(indent + 2)
                        items.append({key: value})
                    else:
                        items.append({key: None})
                        self.index -= 1
                        break
            else:
                items.append(self._parse_inline_value(rest, indent + 2))
        return items

    def _read_multiline_string(self, indent_level: int = 0, prefix: str = None, quote: str = None) -> tuple:
        if prefix is not None:
            content = prefix
            consumed = 0
        else:
            line = self.lines[self.index]
            stripped = line.lstrip()
            if stripped.startswith("'''"):
                quote = "'''"
            elif stripped.startswith('"""'):
                quote = '"""'
            else:
                return '', 1
            end = stripped.find(quote, 3)
            if end != -1:
                content = stripped[3:end]
                content = content.strip('\n')
                self.index += 1
                return content, 1
            content = stripped[3:]
            consumed = 1
            self.index += 1
        while self.index < len(self.lines):
            line = self.lines[self.index]
            stripped_line = line.lstrip()
            pos = stripped_line.find(quote)
            if pos != -1:
                content += '\n' + stripped_line[:pos]
                consumed += 1
                self.index += 1
                content = content.strip('\n')
                return content, consumed
            else:
                line_content = stripped_line
                if quote == '"""':
                    comment_pos = line_content.find('#')
                    if comment_pos != -1:
                        if comment_pos == 0:
                            consumed += 1
                            self.index += 1
                            continue
                        line_content = line_content[:comment_pos].rstrip()
                content += '\n' + line_content
                consumed += 1
                self.index += 1
        raise YACLParseError(f"Unclosed {quote} string")

    def _strip_double_quote_comment(self, content: str) -> str:
        comment_pos = -1
        j = 0
        while j < len(content):
            if content[j] == '\\':
                j += 2
            elif content[j] == '#' and (j == 0 or content[j-1] == ' '):
                comment_pos = j
                break
            else:
                j += 1
        if comment_pos != -1:
            content = content[:comment_pos]
        return content

    def _parse_inline_value(self, text: str, indent_level: int) -> Any:
        text = text.strip()
        if not text:
            return None
        if text.startswith("'''"):
            end = text.find("'''", 3)
            if end != -1:
                return text[3:end].strip('\n')
            return text[3:]
        if text.startswith('"""'):
            end = text.find('"""', 3)
            if end != -1:
                content = text[3:end]
                lines = content.split('\n')
                cleaned = []
                for line in lines:
                    comment_pos = line.find('#')
                    if comment_pos != -1:
                        line = line[:comment_pos]
                    cleaned.append(line.rstrip())
                return '\n'.join(cleaned).strip('\n')
            return text[3:]
        if text.startswith("'") and not text.startswith("'''"):
            i = 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == "'":
                    content = text[1:i]
                    content = content.replace("\\'", "'").replace("\\\\", "\\")
                    return content
                else:
                    i += 1
            content = text[1:]
            content = content.replace("\\'", "'").replace("\\\\", "\\")
            return content
        if text.startswith('"') and not text.startswith('"""'):
            i = 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    content = text[1:i]
                    content = content.replace('\\"', '"').replace('\\\\', '\\')
                    content = self._strip_double_quote_comment(content)
                    return content.rstrip()
                else:
                    i += 1
            content = text[1:]
            content = content.replace('\\"', '"').replace('\\\\', '\\')
            content = self._strip_double_quote_comment(content)
            return content.rstrip()
        if text == 'none':
            return None
        if text in self.TRUE_VALUES:
            return True
        if text in self.FALSE_VALUES:
            return False
        try:
            if '.' in text:
                return float(text)
            else:
                return int(text)
        except ValueError:
            pass
        if text.startswith('['):
            if ']' not in text or text.count('[') != text.count(']'):
                raise YACLParseError(f"Invalid reference syntax: {text}")
            return Reference(text)
        return text

    def _resolve_references(self, data: Any, root: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._resolve_references(v, root) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_references(item, root) for item in data]
        elif isinstance(data, Reference):
            return data.resolve(root)
        else:
            return data


class Reference:
    def __init__(self, path: str):
        self.path = path

    def resolve(self, data: Any) -> Any:
        if not self.path.startswith('['):
            return None
        parts = []
        current = self.path
        while current:
            if current.startswith('['):
                end = current.find(']')
                if end == -1:
                    break
                key = current[1:end]
                parts.append(('key', key))
                current = current[end+1:]
                if current.startswith('.'):
                    current = current[1:]
            else:
                match = re.match(r'^(\d+)', current)
                if match:
                    parts.append(('index', int(match.group(1))))
                    current = current[match.end():]
                    if current.startswith('.'):
                        current = current[1:]
                else:
                    break
        result = data
        for part_type, value in parts:
            if result is None:
                return None
            if part_type == 'key':
                if isinstance(result, dict):
                    result = result.get(value)
                else:
                    return None
            else:
                if isinstance(result, list):
                    if 0 <= value < len(result):
                        result = result[value]
                    else:
                        return None
                else:
                    return None
        return result


# Internal parser instance
_parser = _Parser()


def load(source: Union[str, TextIO]) -> Any:
    """Load YACL from file path or file object."""
    if hasattr(source, 'read'):
        content = source.read()
    elif isinstance(source, str):
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        raise TypeError("source must be file object or file path string")
    data = _parser.parse(content)
    return _parser._resolve_references(data, data)


def loads(content: str) -> Any:
    """Load YACL from string content."""
    if not isinstance(content, str):
        raise TypeError("content must be string")
    data = _parser.parse(content)
    return _parser._resolve_references(data, data)


def dump(data: Any, fp: TextIO, indent: int = 2) -> None:
    """Dump data to file in YACL format."""
    fp.write(dumps(data, indent))


def dumps(data: Any, indent: int = 2) -> str:
    """Dump data to YACL format string."""
    if data is None:
        return 'none'
    if isinstance(data, bool):
        return 'true' if data else 'false'
    if isinstance(data, (int, float)):
        return str(data)
    if isinstance(data, str):
        if '\n' in data:
            return "'''\n" + data + "\n'''"
        if '#' in data:
            return "'" + data + "'"
        return "'" + data + "'"
    if isinstance(data, dict):
        return _dump_dict(data, 0, indent)
    if isinstance(data, list):
        return _dump_list(data, 0, indent)
    return str(data)


def _dump_dict(data: Dict, level: int, indent: int) -> str:
    if not data:
        return ''
    lines = []
    prefix = ' ' * (level * indent)
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            sub = _dump_dict(value, level + 1, indent)
            if sub:
                lines.append(sub)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            sub = _dump_list(value, level + 1, indent)
            if sub:
                lines.append(sub)
        else:
            lines.append(f"{prefix}{key}: {_dump_value(value)}")
    return '\n'.join(lines)


def _dump_list(data: List, level: int, indent: int) -> str:
    if not data:
        return ''
    lines = []
    prefix = ' ' * (level * indent)
    item_prefix = ' ' * ((level + 1) * indent - 2) + '- '
    for item in data:
        if isinstance(item, dict):
            lines.append(f"{prefix}-")
            for key, value in item.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}  {key}:")
                    sub = _dump_dict(value, level + 2, indent)
                    if sub:
                        lines.append(sub)
                elif isinstance(value, list):
                    lines.append(f"{prefix}  {key}:")
                    sub = _dump_list(value, level + 2, indent)
                    if sub:
                        lines.append(sub)
                else:
                    lines.append(f"{prefix}  {key}: {_dump_value(value)}")
        elif isinstance(item, list):
            lines.append(f"{prefix}-")
            sub = _dump_list(item, level + 1, indent)
            if sub:
                lines.append(sub)
        else:
            lines.append(f"{item_prefix}{_dump_value(item)}")
    return '\n'.join(lines)


def _dump_value(value: Any) -> str:
    if value is None:
        return 'none'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if '\n' in value:
            return "'''\n" + value + "\n'''"
        if '#' in value:
            return "'" + value + "'"
        return "'" + value + "'"
    return str(value)


__version__ = '0.1.0'
__all__ = ['load', 'loads', 'dump', 'dumps', 'YACLParseError']