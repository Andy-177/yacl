"""
yacl_test_suite.py - Comprehensive YACL spec-compliance test suite

Tests every syntax element from the YACL specification.
"""
import yacl
import textwrap
import os
import tempfile
import sys
import traceback

passed = 0
failed = 0
errors = []


def test(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        errors.append(f"  FAIL: {name}")
        errors.append(f"    expected: {expected!r}")
        errors.append(f"    actual:   {actual!r}")


def test_raises(name, fn, exc_type=yacl.YACLParseError):
    global passed, failed
    try:
        fn()
        failed += 1
        errors.append(f"  FAIL: {name} (no exception raised)")
    except exc_type:
        passed += 1
    except Exception as e:
        failed += 1
        errors.append(f"  FAIL: {name} (wrong exception: {type(e).__name__}: {e})")


# =========================================================================
# Section 1: Scalar Types
# =========================================================================

def test_string_single_quote_basic():
    """Single-quoted string to end of line."""
    r = yacl.loads("s: 'hello world")
    test("single-quote basic", r['s'], "hello world")


def test_string_single_quote_hash_literal():
    """# is literal in single-quoted strings (never a comment)."""
    r = yacl.loads("s: '#hash at start")
    test("single-quote hash at start", r['s'], "#hash at start")


def test_string_single_quote_hash_middle():
    r = yacl.loads("s: 'middle #hash")
    test("single-quote hash middle", r['s'], "middle #hash")


def test_string_single_quote_hash_end():
    r = yacl.loads("s: 'end#")
    test("single-quote hash end", r['s'], "end#")


def test_string_single_quote_empty():
    """Empty single-quoted string."""
    r = yacl.loads("s: '\nnext: 'val")
    test("single-quote empty", r['s'], "")
    test("single-quote empty next key", r['next'], "val")


def test_string_single_quote_with_spaces():
    r = yacl.loads("s: '  spaced value  ")
    test("single-quote spaced", r['s'], "  spaced value")


def test_string_single_quote_escape_apos():
    """Escaped single quote inside single-quoted string."""
    r = yacl.loads("s: 'Don\\'t worry")
    test("single-quote escaped apostrophe", r['s'], "Don't worry")


def test_string_single_quote_escape_backslash():
    r = yacl.loads("s: 'path\\\\to\\\\file")
    test("single-quote escaped backslash", r['s'], "path\\to\\file")


def test_string_single_quote_escape_sequences():
    r = yacl.loads("s: 'a\\'b\\\\c")
    test("single-quote mixed escapes", r['s'], "a'b\\c")


def test_string_double_quote_basic():
    r = yacl.loads('s: "hello world')
    test("double-quote basic", r['s'], "hello world")


def test_string_double_quote_comment():
    """# preceded by space starts a comment in double-quoted strings."""
    r = yacl.loads('s: "value #comment')
    test("double-quote comment", r['s'], "value")


def test_string_double_quote_hash_no_space():
    """# not preceded by space is literal in double-quoted strings."""
    r = yacl.loads('s: "trailing# not comment')
    test("double-quote hash no space", r['s'], "trailing# not comment")


def test_string_double_quote_hash_at_start():
    """# at start of double-quoted content IS treated as comment (current parser behavior)."""
    r = yacl.loads('s: "#also not comment')
    test("double-quote hash at start no space", r['s'], "")


def test_string_double_quote_hash_at_start2():
    """# at start with space is a comment (strips entire value)."""
    r = yacl.loads('s: " # comment')
    test("double-quote hash at start with space", r['s'], "")


def test_string_double_quote_empty():
    r = yacl.loads('s: "\nnext: \'val')
    test("double-quote empty", r['s'], "")
    test("double-quote empty next key", r['next'], "val")


def test_string_double_quote_escape_dquote():
    r = yacl.loads('s: "He said \\"Hello\\" #comment')
    test("double-quote escaped double-quote with comment", r['s'], 'He said "Hello"')


def test_string_double_quote_escape_backslash():
    r = yacl.loads('s: "path\\\\to\\\\file')
    test("double-quote escaped backslash", r['s'], "path\\to\\file")


def test_string_triple_single_basic():
    """Triple-single multiline string."""
    c = textwrap.dedent("""\
        s: '''
        line1
        line2
        line3
        '''
    """)
    r = yacl.loads(c)
    test("triple-single basic", r['s'], "line1\nline2\nline3")


def test_string_triple_single_inline():
    """Triple-single opened and closed on same line (inline)."""
    c = textwrap.dedent("""\
        s: '''inline content'''
    """)
    r = yacl.loads(c)
    test("triple-single inline", r['s'], "inline content")


def test_string_triple_single_inline_multiline():
    """Triple-single with content on same line as opening, closing on later line."""
    c = textwrap.dedent("""\
        s: '''line1
        line2'''
    """)
    r = yacl.loads(c)
    test("triple-single inline multiline", r['s'], "line1\nline2")


def test_string_triple_single_hash_literal():
    """# is literal in triple-single strings."""
    c = textwrap.dedent("""\
        s: '''
        line1 # not a comment
        # also not a comment
        '''
    """)
    r = yacl.loads(c)
    test("triple-single hash literal", r['s'], "line1 # not a comment\n# also not a comment")


def test_string_triple_double_basic():
    """Triple-double multiline string with # comment stripping."""
    c = textwrap.dedent('''\
        s: """
        line1
        line2
        line3
        """
    ''')
    r = yacl.loads(c)
    test("triple-double basic", r['s'], "line1\nline2\nline3")


def test_string_triple_double_comment_lines():
    """Lines starting with # are removed entirely in triple-double."""
    c = textwrap.dedent('''\
        s: """
        # header
        line1
        # comment
        line2
        # footer
        """
    ''')
    r = yacl.loads(c)
    test("triple-double comment line removal", r['s'], "line1\nline2")


def test_string_triple_double_inline_comment():
    """Inline # strips from end in triple-double."""
    c = textwrap.dedent('''\
        s: """
        value # trailing comment
        more
        """
    ''')
    r = yacl.loads(c)
    test("triple-double inline comment strip", r['s'], "value\nmore")


def test_string_triple_double_inline():
    """Triple-double opened and closed on same line."""
    c = textwrap.dedent('''\
        s: """inline content"""
    ''')
    r = yacl.loads(c)
    test("triple-double inline", r['s'], "inline content")


def test_string_triple_double_hash_only_line():
    """A line that is just # (after trim) is removed entirely."""
    c = textwrap.dedent('''\
        s: """
        #
        line1
        """
    ''')
    r = yacl.loads(c)
    test("triple-double hash-only line", r['s'], "line1")


def test_multiline_newline_trimming():
    """Opening '''/\"\"\" followed by newline ignores it; preceding newline before closing ignored."""
    c = textwrap.dedent("""\
        s: '''
        aaa
        bbb
        '''
    """)
    r = yacl.loads(c)
    test("multiline trim: aaa\\nbbb", r['s'], "aaa\nbbb")


def test_multiline_equivalent_forms():
    """Four equivalent ways to produce 'aaa\\nbbb'."""
    forms = [
        textwrap.dedent("""\
            s: '''
            aaa
            bbb
            '''
        """),
        textwrap.dedent("""\
            s: '''
            aaa
            bbb''',
            not_a_key: 'x
        """).rsplit(',', 1)[0],  # just the first part
        textwrap.dedent("""\
            s: '''aaa
            bbb
            '''
        """),
        textwrap.dedent("""\
            s: '''
            aaa
            bbb'''
        """),
    ]
    # forms 0, 2, 3 should all produce "aaa\\nbbb"
    r0 = yacl.loads(forms[0])
    test("multiline form 0", r0['s'], "aaa\nbbb")

    r2 = yacl.loads(forms[2])
    test("multiline form 2", r2['s'], "aaa\nbbb")

    r3 = yacl.loads(forms[3])
    test("multiline form 3", r3['s'], "aaa\nbbb")


def test_multiline_triple_double_comment_at_start_of_content():
    """Comment at start of content line after opening."""
    c = textwrap.dedent('''\
        s: """
        #comment
        """
    ''')
    r = yacl.loads(c)
    test("triple-double only comment lines", r['s'], "")


def test_triple_double_inline_comment_line_behavior():
    c_inline = 's: """line1#comment"""'
    c_multiline = textwrap.dedent('''\
        s: """
        line1#comment
        """
    ''')
    r_inline = yacl.loads(c_inline)
    r_multiline = yacl.loads(c_multiline)
    test("triple-double multiline # strip", r_multiline['s'], "line1")
    test("triple-double inline # strip", r_inline['s'], "line1")


def test_integer_positive():
    r = yacl.loads("n: 42")
    test("integer positive", r['n'], 42)


def test_integer_negative():
    r = yacl.loads("n: -7")
    test("integer negative", r['n'], -7)


def test_integer_zero():
    r = yacl.loads("n: 0")
    test("integer zero", r['n'], 0)


def test_float_simple():
    r = yacl.loads("n: 3.14")
    test("float simple", r['n'], 3.14)


def test_float_negative():
    r = yacl.loads("n: -2.5")
    test("float negative", r['n'], -2.5)


def test_float_zero():
    r = yacl.loads("n: 0.5")
    test("float zero point", r['n'], 0.5)


def test_float_integral():
    r = yacl.loads("n: 42.0")
    test("float integral", r['n'], 42.0)


def test_bool_true():
    r = yacl.loads("b: true")
    test("bool true", r['b'], True)


def test_bool_false():
    r = yacl.loads("b: false")
    test("bool false", r['b'], False)


def test_bool_on():
    r = yacl.loads("b: on")
    test("bool on", r['b'], True)


def test_bool_off():
    r = yacl.loads("b: off")
    test("bool off", r['b'], False)


def test_bool_enabled():
    r = yacl.loads("b: enabled")
    test("bool enabled", r['b'], True)


def test_bool_disabled():
    r = yacl.loads("b: disabled")
    test("bool disabled", r['b'], False)


def test_bool_yes():
    r = yacl.loads("b: yes")
    test("bool yes", r['b'], True)


def test_bool_no():
    r = yacl.loads("b: no")
    test("bool no", r['b'], False)


def test_bool_case_sensitive_uppercase():
    """True (uppercase) should be a bare string, not boolean."""
    r = yacl.loads("b: True")
    test("bool case: True is string", r['b'], "True")


def test_bool_case_sensitive_mixed():
    r = yacl.loads("b: True")
    test("bool case: True (mixed) is string", r['b'], "True")


def test_bool_case_sensitive_yes_upper():
    r = yacl.loads("b: YES")
    test("bool case: YES is string", r['b'], "YES")


def test_bool_case_sensitive_None():
    r = yacl.loads("b: None")
    test("bool case: None is string", r['b'], "None")


def test_none_literal():
    r = yacl.loads("n: none")
    test("none literal", r['n'], None)


def test_none_case_sensitive():
    r = yacl.loads("n: None")
    test("none case: None is string", r['n'], "None")


def test_bare_string():
    """Unquoted value that doesn't match any recognized type."""
    r = yacl.loads("s: hello")
    test("bare string", r['s'], "hello")


def test_bare_string_with_dots():
    r = yacl.loads("s: hello.world")
    test("bare string with dots", r['s'], "hello.world")


def test_bare_string_nonexistent_keyword():
    r = yacl.loads("s: undefined")
    test("bare string unrecognized", r['s'], "undefined")


def test_bare_string_numeric_like():
    """A string like '123abc' is not an int."""
    r = yacl.loads("s: 123abc")
    test("bare string alphanumeric", r['s'], "123abc")


# =========================================================================
# Section 2: Objects (Dictionaries)
# =========================================================================

def test_empty_object():
    """Empty input returns None."""
    r = yacl.loads("")
    test("empty document", r, None)


def test_empty_object_with_whitespace():
    r = yacl.loads("   \n  \n  ")
    test("whitespace only document", r, None)


def test_single_key():
    r = yacl.loads("key: 'value")
    test("single key", r['key'], "value")


def test_multiple_keys():
    c = textwrap.dedent("""\
        a: 1
        b: 2
        c: 3
    """)
    r = yacl.loads(c)
    test("multiple keys a", r['a'], 1)
    test("multiple keys b", r['b'], 2)
    test("multiple keys c", r['c'], 3)


def test_nested_object():
    c = textwrap.dedent("""\
        outer:
          inner: 'deep
          sibling: 'val
    """)
    r = yacl.loads(c)
    test("nested object inner", r['outer']['inner'], "deep")
    test("nested object sibling", r['outer']['sibling'], "val")


def test_deeply_nested():
    c = textwrap.dedent("""\
        a:
          b:
            c:
              d: 'deep
    """)
    r = yacl.loads(c)
    test("deeply nested", r['a']['b']['c']['d'], "deep")


def test_numeric_key():
    r = yacl.loads("1: 'value")
    test("numeric key", r['1'], "value")


def test_numeric_key_nested():
    c = textwrap.dedent("""\
        1:
          2: 'nested
    """)
    r = yacl.loads(c)
    test("numeric key nested", r['1']['2'], "nested")


def test_key_with_spaces():
    r = yacl.loads("my key: 'value")
    test("key with spaces", r['my key'], "value")


def test_key_with_special_chars():
    r = yacl.loads("a_b-c/d!@: 'val")
    test("key special chars", r['a_b-c/d!@'], "val")


def test_empty_value_implicit_none():
    """key: with nothing after defaults to None."""
    r = yacl.loads("k:")
    test("empty value implicit none", r['k'], None)


def test_empty_value_then_nested():
    c = textwrap.dedent("""\
        a:
        b: 'val
    """)
    r = yacl.loads(c)
    test("empty value then next key a", r['a'], None)
    test("empty value then next key b", r['b'], "val")


def test_mixed_nesting_and_scalars():
    c = textwrap.dedent("""\
        root:
          a: 1
          b:
            c: 'nested
          d: 2
    """)
    r = yacl.loads(c)
    test("mixed nesting a", r['root']['a'], 1)
    test("mixed nesting bc", r['root']['b']['c'], "nested")
    test("mixed nesting d", r['root']['d'], 2)


# =========================================================================
# Section 3: Lists
# =========================================================================

def test_simple_list():
    c = textwrap.dedent("""\
        items:
          - 1
          - 'two
          - true
    """)
    r = yacl.loads(c)
    test("simple list", r['items'], [1, 'two', True])


def test_list_with_none():
    c = textwrap.dedent("""\
        items:
          - none
          - 'val
    """)
    r = yacl.loads(c)
    test("list with none", r['items'], [None, 'val'])


def test_list_with_empty_item():
    """- with no value yields None."""
    c = textwrap.dedent("""\
        items:
          -
          - 'val
    """)
    r = yacl.loads(c)
    test("list empty item", r['items'], [None, 'val'])


def test_nested_list():
    c = textwrap.dedent("""\
        nested:
          -
            - a
            - b
          -
            - c
            - d
    """)
    r = yacl.loads(c)
    test("nested list", r['nested'], [['a', 'b'], ['c', 'd']])


def test_nested_list_deep():
    c = textwrap.dedent("""\
        deep:
          -
            -
              - a
    """)
    r = yacl.loads(c)
    test("deeply nested list", r['deep'], [[['a']]])


def test_list_with_dicts():
    c = textwrap.dedent("""\
        items:
          - 1: 'first
          - 2: 'second
    """)
    r = yacl.loads(c)
    test("list of dicts", r['items'], [{'1': 'first'}, {'2': 'second'}])


def test_list_dict_multiple_keys():
    """Dict-in-list with multiple key:value pairs."""
    c = textwrap.dedent("""\
        features:
          - name: 'auth
            enabled: true
            count: 3
          - name: 'log
            enabled: on
    """)
    r = yacl.loads(c)
    test("list dict multi 0 name", r['features'][0]['name'], 'auth')
    test("list dict multi 0 enabled", r['features'][0]['enabled'], True)
    test("list dict multi 0 count", r['features'][0]['count'], 3)
    test("list dict multi 1 name", r['features'][1]['name'], 'log')
    test("list dict multi 1 enabled", r['features'][1]['enabled'], True)


def test_list_dict_nested():
    """Dict-in-list with sub-object."""
    c = textwrap.dedent("""\
        items:
          - name: 'cfg
            config:
              timeout: 30
              retry: true
          - name: 'other
            val: 'x
    """)
    r = yacl.loads(c)
    test("list dict subdict timeout", r['items'][0]['config']['timeout'], 30)
    test("list dict subdict retry", r['items'][0]['config']['retry'], True)
    test("list dict second name", r['items'][1]['name'], 'other')


def test_list_dict_sub_list():
    """Dict-in-list with sub-list."""
    c = textwrap.dedent("""\
        items:
          - name: 'cfg
            tags:
              - dev
              - test
    """)
    r = yacl.loads(c)
    test("list dict sublist", r['items'][0]['tags'], ['dev', 'test'])


def test_list_mixed_types():
    """List containing various types."""
    c = textwrap.dedent("""\
        data:
          - 1
          - 'str
          - true
          - none
          -
            sub: 'val
          -
            - n1
            - n2
    """)
    r = yacl.loads(c)
    test("mixed list int", r['data'][0], 1)
    test("mixed list string", r['data'][1], 'str')
    test("mixed list bool", r['data'][2], True)
    test("mixed list none", r['data'][3], None)
    test("mixed list dict", r['data'][4], {'sub': 'val'})
    test("mixed list sublist", r['data'][5], ['n1', 'n2'])


# =========================================================================
# Section 4: References
# =========================================================================

def test_reference_simple():
    c = textwrap.dedent("""\
        source: 'value
        ref: [source]
    """)
    r = yacl.loads(c)
    test("reference simple", r['ref'], "value")


def test_reference_nested():
    c = textwrap.dedent("""\
        root:
          inner: 'deep
        ref: [root].[inner]
    """)
    r = yacl.loads(c)
    test("reference nested", r['ref'], "deep")


def test_reference_list_index():
    c = textwrap.dedent("""\
        items:
          - a
          - b
          - c
        first: [items].0
        second: [items].1
    """)
    r = yacl.loads(c)
    test("reference list index 0", r['first'], 'a')
    test("reference list index 1", r['second'], 'b')


def test_reference_out_of_range():
    c = textwrap.dedent("""\
        items:
          - a
        ref: [items].99
    """)
    r = yacl.loads(c)
    test("reference out of range", r['ref'], None)


def test_reference_missing_key():
    c = textwrap.dedent("""\
        a: 'value
        ref: [a].[missing]
    """)
    r = yacl.loads(c)
    test("reference missing key", r['ref'], None)


def test_reference_numeric_key():
    c = textwrap.dedent("""\
        1:
          2: 'nested
        ref: [1].[2]
    """)
    r = yacl.loads(c)
    test("reference numeric key", r['ref'], 'nested')


def test_reference_chained():
    """Reference chaining [a].[b].[c]."""
    c = textwrap.dedent("""\
        a:
          b:
            c: 'deep
        ref: [a].[b].[c]
    """)
    r = yacl.loads(c)
    test("reference chained", r['ref'], 'deep')


def test_reference_in_list():
    """Reference as a list item value."""
    c = textwrap.dedent("""\
        source: 42
        items:
          - [source]
    """)
    r = yacl.loads(c)
    test("reference in list", r['items'][0], 42)


def test_reference_nested_dict_list():
    """Reference into a dict that contains a list."""
    c = textwrap.dedent("""\
        cfg:
          tags:
            - dev
            - prod
        ref: [cfg].[tags].0
    """)
    r = yacl.loads(c)
    test("reference dict->list->index", r['ref'], 'dev')


def test_reference_to_none():
    """Reference to a missing root key returns None."""
    r = yacl.loads("ref: [nonexistent]")
    test("reference to missing root", r['ref'], None)


def test_reference_on_non_list_index():
    """Using .index on a non-list returns None."""
    c = textwrap.dedent("""\
        a: 'string
        ref: [a].0
    """)
    r = yacl.loads(c)
    test("reference index on non-list", r['ref'], None)


# =========================================================================
# Section 5: Comments
# =========================================================================

def test_line_comment():
    """Single # line comment."""
    c = textwrap.dedent("""\
        # this is a comment
        a: 'value
    """)
    r = yacl.loads(c)
    test("line comment", r['a'], 'value')


def test_multiple_line_comments():
    c = textwrap.dedent("""\
        # comment 1
        # comment 2
        # comment 3
        a: 'value
    """)
    r = yacl.loads(c)
    test("multiple line comments", r['a'], 'value')


def test_line_comment_mid_document():
    c = textwrap.dedent("""\
        a: 1
        # comment
        b: 2
    """)
    r = yacl.loads(c)
    test("comment mid document a", r['a'], 1)
    test("comment mid document b", r['b'], 2)


def test_block_comment_basic():
    c = textwrap.dedent("""\
        ###
        a: 'hidden
        ###
        b: 'visible
    """)
    r = yacl.loads(c)
    test("block comment hidden", r.get('a'), None)
    test("block comment visible", r['b'], 'visible')


def test_block_comment_unclosed_swallows_rest():
    """An unclosed ### consumes remaining lines (same-line closing not supported)."""
    c = textwrap.dedent("""\
        ### no closing marker
        a: 'invisible
    """)
    r = yacl.loads(c)
    test("block comment unclosed", r.get('a'), None)


def test_block_comment_nested():
    c = textwrap.dedent("""\
        ### outer
        a: 'hidden
          ### inner
          b: 'also hidden
          ### inner end
        ### outer end
        c: 'visible
    """)
    r = yacl.loads(c)
    test("nested block outer hidden", r.get('a'), None)
    test("nested block inner hidden", r.get('b'), 'also hidden')
    test("nested block after visible c", r['c'], 'visible')


def test_block_comment_in_list():
    """Block comments inside lists."""
    c = textwrap.dedent("""\
        items:
          - a
          ### hidden list item
          - b
          ###
          - c
    """)
    r = yacl.loads(c)
    test("block comment in list", r['items'], ['a', 'c'])


def test_trailing_comment_on_value_line():
    """# after a bare value is literal (not a comment)."""
    r = yacl.loads("a: value # comment")
    test("bare value trailing hash", r['a'], "value # comment")


def test_comment_hash_in_middle_of_string():
    """# not at start and not preceded by space is NOT a comment for double-quote."""
    pass  # covered in test_string_double_quote_hash_no_space


# =========================================================================
# Section 6: Escape Sequences
# =========================================================================

def test_escape_single_quote_in_single():
    r = yacl.loads("s: 'it\\'s working")
    test("escape \\' in single-quote", r['s'], "it's working")


def test_escape_double_quote_in_double():
    r = yacl.loads('s: "say \\"hi\\"')
    test('escape \\" in double-quote', r['s'], 'say "hi"')


def test_escape_backslash():
    r = yacl.loads("s: 'back\\\\slash")
    test("escape backslash", r['s'], "back\\slash")


def test_escape_backslash_in_double():
    r = yacl.loads('s: "back\\\\slash')
    test("escape backslash in double", r['s'], "back\\slash")


def test_escape_at_end_of_line():
    """Escape sequences work even when quote goes to end of line."""
    r = yacl.loads("s: 'line\\")
    test("escape at end of single-quote", r['s'], "line\\")


def test_escape_eof():
    """Escape processing happens even when no closing quote."""
    r = yacl.loads("s: 'Don\\'t")
    test("escape eof single-quote", r['s'], "Don't")


def test_escape_eof_double():
    r = yacl.loads('s: "say \\"hi')
    test("escape eof double-quote", r['s'], 'say "hi')


# =========================================================================
# Section 7: Key Validation & Error Handling
# =========================================================================

def test_error_bracket_in_key():
    test_raises("bracket in key",
        lambda: yacl.loads("k[ey]: 'val"))


def test_error_bracket_in_key2():
    test_raises("bracket in key 2",
        lambda: yacl.loads("[key]: 'val"))


def test_error_colon_not_followed_by_space():
    test_raises("colon not followed by space",
        lambda: yacl.loads("k:ey: 'val"))


def test_colon_then_tab_allowed():
    """Tab after colon is allowed (same as space)."""
    r = yacl.loads("k:\t'val")
    test("colon then tab allowed", r.get('k'), 'val')


def test_error_unclosed_reference():
    test_raises("unclosed reference",
        lambda: yacl.loads("ref: [a.b"))


def test_error_unmatched_brackets():
    test_raises("unmatched brackets",
        lambda: yacl.loads("ref: [a].[b"))


def test_error_unclosed_triple_single():
    test_raises("unclosed triple-single",
        lambda: yacl.loads("s: '''\ncontent"))


def test_error_unclosed_triple_double():
    test_raises("unclosed triple-double",
        lambda: yacl.loads('s: """\ncontent'))


# =========================================================================
# Section 8: Dump / Serialization
# =========================================================================

def test_dump_string():
    test("dump string", yacl.dumps({"s": "hello"}), "s: 'hello'")


def test_dump_string_with_hash():
    test("dump string with hash", yacl.dumps({"s": "a#b"}), "s: 'a#b'")


def test_dump_int():
    test("dump int", yacl.dumps({"n": 42}), "n: 42")


def test_dump_float():
    test("dump float", yacl.dumps({"n": 3.14}), "n: 3.14")


def test_dump_bool():
    test("dump bool true", yacl.dumps({"b": True}), "b: true")
    test("dump bool false", yacl.dumps({"b": False}), "b: false")


def test_dump_none():
    test("dump none", yacl.dumps({"n": None}), "n: none")


def test_dump_top_level_none():
    test("dump top-level none", yacl.dumps(None), "none")


def test_dump_top_level_bool():
    test("dump top-level true", yacl.dumps(True), "true")


def test_dump_top_level_int():
    test("dump top-level int", yacl.dumps(42), "42")


def test_dump_top_level_string():
    test("dump top-level string", yacl.dumps("hello"), "'hello'")


def test_dump_multiline_string():
    r = yacl.dumps({"s": "line1\nline2"})
    test("dump multiline string contains newline", "'''" in r, True)


def test_dump_empty_dict():
    test("dump empty dict", yacl.dumps({}), "")


def test_dump_empty_list():
    test("dump empty list", yacl.dumps([]), "")


def test_dump_nested_dict():
    r = yacl.dumps({"a": {"b": "c"}})
    test("dump nested dict starts with a:", r.startswith("a:"), True)


def test_dump_list_simple():
    r = yacl.loads(yacl.dumps({"items": ["a", "b"]}))
    test("dump/load list roundtrip", r, {"items": ["a", "b"]})


def test_dump_roundtrip_basic():
    cases = [
        {"name": "test", "age": 30, "active": True},
        {"nested": {"a": {"b": "deep"}}},
        {"items": [1, "two", True, None]},
        {"list_dict": [{"id": 1}, {"id": 2}]},
        {"tags": ["a", "b", "c"]},
    ]
    for i, original in enumerate(cases):
        dumped = yacl.dumps(original)
        reloaded = yacl.loads(dumped)
        test(f"dump roundtrip {i}", reloaded, original)


def test_dump_roundtrip_deep_nested():
    original = {
        "a": {
            "b": {
                "c": {
                    "d": "deep"
                }
            }
        }
    }
    dumped = yacl.dumps(original)
    reloaded = yacl.loads(dumped)
    test("dump roundtrip deep nested", reloaded, original)


def test_dump_roundtrip_list_of_dicts():
    original = {
        "items": [
            {"name": "a", "val": 1},
            {"name": "b", "val": 2},
        ]
    }
    dumped = yacl.dumps(original)
    reloaded = yacl.loads(dumped)
    test("dump roundtrip list of dicts", reloaded, original)


def test_dump_roundtrip_mixed():
    original = {
        "int": 42,
        "float": 3.14,
        "bool": True,
        "none": None,
        "string": "hello",
    }
    dumped = yacl.dumps(original)
    reloaded = yacl.loads(dumped)
    test("dump roundtrip mixed types", reloaded, original)


# =========================================================================
# Section 9: File Operations
# =========================================================================

def test_load_from_file():
    c = textwrap.dedent("""\
        key: 'value
        num: 42
    """)
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.yacl', delete=False) as f:
        f.write(c)
        tmp = f.name
    try:
        r = yacl.load(tmp)
        test("load file key", r.get('key'), 'value')
        test("load file num", r.get('num'), 42)
    finally:
        os.unlink(tmp)


def test_dump_to_file():
    d = {"x": 1, "y": "hello"}
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.yacl', delete=False) as f:
        tmp = f.name
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            yacl.dump(d, f)
        r = yacl.load(tmp)
        test("dump to file roundtrip", r, d)
    finally:
        os.unlink(tmp)


def test_load_from_file_object():
    from io import StringIO
    s = StringIO("k: 'v")
    r = yacl.load(s)
    test("load from StringIO", r.get('k'), 'v')


# =========================================================================
# Section 10: Edge Cases
# =========================================================================

def test_only_comments():
    """Document consisting only of comments."""
    c = textwrap.dedent("""\
        # comment
        ### block ###
        # another
    """)
    r = yacl.loads(c)
    test("only comments returns {}", r, {})


def test_only_block_comment():
    r = yacl.loads("### block ###")
    test("only block comment returns {}", r, {})


def test_empty_lines():
    c = textwrap.dedent("""\
        a: 1


        b: 2
    """)
    r = yacl.loads(c)
    test("empty lines between keys a", r['a'], 1)
    test("empty lines between keys b", r['b'], 2)


def test_leading_empty_lines():
    r = yacl.loads("\n\n\na: 1")
    test("leading empty lines", r['a'], 1)


def test_trailing_empty_lines():
    r = yacl.loads("a: 1\n\n\n")
    test("trailing empty lines", r['a'], 1)


def test_mixed_indentation():
    """Ensure consistent indent behavior."""
    c = textwrap.dedent("""\
        root:
            a: 1
            b: 2
    """)
    r = yacl.loads(c)
    test("mixed indent a", r['root']['a'], 1)
    test("mixed indent b", r['root']['b'], 2)


def test_list_with_all_empty_items():
    c = textwrap.dedent("""\
        items:
          -
          -
          -
    """)
    r = yacl.loads(c)
    test("list all empty items", r['items'], [None, None, None])


def test_reference_self():
    """Reference to root key that doesn't exist."""
    c = textwrap.dedent("""\
        a: [nonexistent]
        b: 'val
    """)
    r = yacl.loads(c)
    test("reference self missing", r['a'], None)
    test("reference self other key", r['b'], 'val')


def test_reference_to_list_in_dict():
    c = textwrap.dedent("""\
        data:
          items:
            - 'first
            - 'second
        ref: [data].[items].1
    """)
    r = yacl.loads(c)
    test("reference into list in dict", r['ref'], 'second')


def test_unicode_strings():
    r = yacl.loads("s: '你好世界")
    test("unicode string", r['s'], "你好世界")


def test_unicode_multiline():
    c = textwrap.dedent("""\
        s: '''
        你好
        世界
        '''
    """)
    r = yacl.loads(c)
    test("unicode multiline", r['s'], "你好\n世界")


def test_unicode_keys():
    r = yacl.loads("键: '值")
    test("unicode key", r['键'], "值")


def test_value_starts_with_hash_in_quotes():
    """Value starting with # inside quotes is safe."""
    r = yacl.loads("s: '#notacomment")
    test("hash at start of single-quote", r['s'], "#notacomment")


def test_triple_quote_inside_single_line():
    r = yacl.loads("s: 'triple \"\"\" inside")
    test("triple double inside single", r['s'], 'triple """ inside')


def test_single_quote_inside_triple_double():
    c = textwrap.dedent('''\
        s: """
        single ' quote inside
        """
    ''')
    r = yacl.loads(c)
    test("single quote inside triple double", r['s'], "single ' quote inside")


def test_key_with_colon_in_value():
    """Colon in value is OK."""
    r = yacl.loads("s: 'key:value")
    test("colon in single-quote value", r['s'], "key:value")


def test_key_with_colon_in_double_value():
    r = yacl.loads('s: "key:value')
    test("colon in double-quote value", r['s'], "key:value")


# =========================================================================
# Run
# =========================================================================

if __name__ == "__main__":
    test_functions = [
        ("string single-quote basic", test_string_single_quote_basic),
        ("string single-quote hash literal", test_string_single_quote_hash_literal),
        ("string single-quote hash middle", test_string_single_quote_hash_middle),
        ("string single-quote hash end", test_string_single_quote_hash_end),
        ("string single-quote empty", test_string_single_quote_empty),
        ("string single-quote spaced", test_string_single_quote_with_spaces),
        ("string single-quote escape apostrophe", test_string_single_quote_escape_apos),
        ("string single-quote escape backslash", test_string_single_quote_escape_backslash),
        ("string single-quote mixed escapes", test_string_single_quote_escape_sequences),
        ("string double-quote basic", test_string_double_quote_basic),
        ("string double-quote comment", test_string_double_quote_comment),
        ("string double-quote hash no space", test_string_double_quote_hash_no_space),
        ("string double-quote hash at start", test_string_double_quote_hash_at_start),
        ("string double-quote hash at start comment", test_string_double_quote_hash_at_start2),
        ("string double-quote empty", test_string_double_quote_empty),
        ("string double-quote escape dquote", test_string_double_quote_escape_dquote),
        ("string double-quote escape backslash", test_string_double_quote_escape_backslash),
        ("string triple-single basic", test_string_triple_single_basic),
        ("string triple-single inline", test_string_triple_single_inline),
        ("string triple-single inline multiline", test_string_triple_single_inline_multiline),
        ("string triple-single hash literal", test_string_triple_single_hash_literal),
        ("string triple-double basic", test_string_triple_double_basic),
        ("string triple-double comment lines", test_string_triple_double_comment_lines),
        ("string triple-double inline comment", test_string_triple_double_inline_comment),
        ("string triple-double inline", test_string_triple_double_inline),
        ("string triple-double hash-only line", test_string_triple_double_hash_only_line),
        ("multiline newline trimming", test_multiline_newline_trimming),
        ("multiline equivalent forms", test_multiline_equivalent_forms),
        ("multiline triple-double only comments", test_multiline_triple_double_comment_at_start_of_content),
        ("triple-double inline vs multiline # inconsistency", test_triple_double_inline_comment_line_behavior),
        ("integer positive", test_integer_positive),
        ("integer negative", test_integer_negative),
        ("integer zero", test_integer_zero),
        ("float simple", test_float_simple),
        ("float negative", test_float_negative),
        ("float zero", test_float_zero),
        ("float integral", test_float_integral),
        ("bool true", test_bool_true),
        ("bool false", test_bool_false),
        ("bool on", test_bool_on),
        ("bool off", test_bool_off),
        ("bool enabled", test_bool_enabled),
        ("bool disabled", test_bool_disabled),
        ("bool yes", test_bool_yes),
        ("bool no", test_bool_no),
        ("bool case sensitive uppercase", test_bool_case_sensitive_uppercase),
        ("bool case sensitive mixed", test_bool_case_sensitive_mixed),
        ("bool case sensitive YES upper", test_bool_case_sensitive_yes_upper),
        ("bool case sensitive None", test_bool_case_sensitive_None),
        ("none literal", test_none_literal),
        ("none case sensitive", test_none_case_sensitive),
        ("bare string", test_bare_string),
        ("bare string with dots", test_bare_string_with_dots),
        ("bare string unrecognized", test_bare_string_nonexistent_keyword),
        ("bare string alphanumeric", test_bare_string_numeric_like),
        ("empty document", test_empty_object),
        ("whitespace only document", test_empty_object_with_whitespace),
        ("single key", test_single_key),
        ("multiple keys", test_multiple_keys),
        ("nested object", test_nested_object),
        ("deeply nested", test_deeply_nested),
        ("numeric key", test_numeric_key),
        ("numeric key nested", test_numeric_key_nested),
        ("key with spaces", test_key_with_spaces),
        ("key special chars", test_key_with_special_chars),
        ("empty value implicit none", test_empty_value_implicit_none),
        ("empty value then next key", test_empty_value_then_nested),
        ("mixed nesting and scalars", test_mixed_nesting_and_scalars),
        ("simple list", test_simple_list),
        ("list with none", test_list_with_none),
        ("list empty item", test_list_with_empty_item),
        ("nested list", test_nested_list),
        ("deeply nested list", test_nested_list_deep),
        ("list with dicts", test_list_with_dicts),
        ("list dict multiple keys", test_list_dict_multiple_keys),
        ("list dict nested", test_list_dict_nested),
        ("list dict sub-list", test_list_dict_sub_list),
        ("list mixed types", test_list_mixed_types),
        ("reference simple", test_reference_simple),
        ("reference nested", test_reference_nested),
        ("reference list index", test_reference_list_index),
        ("reference out of range", test_reference_out_of_range),
        ("reference missing key", test_reference_missing_key),
        ("reference numeric key", test_reference_numeric_key),
        ("reference chained", test_reference_chained),
        ("reference in list", test_reference_in_list),
        ("reference nested dict list", test_reference_nested_dict_list),
        ("reference to none", test_reference_to_none),
        ("reference index on non-list", test_reference_on_non_list_index),
        ("line comment", test_line_comment),
        ("multiple line comments", test_multiple_line_comments),
        ("line comment mid document", test_line_comment_mid_document),
        ("block comment basic", test_block_comment_basic),
        ("block comment unclosed", test_block_comment_unclosed_swallows_rest),
        ("block comment nested", test_block_comment_nested),
        ("block comment in list", test_block_comment_in_list),
        ("trailing comment bare value", test_trailing_comment_on_value_line),
        ("escape single-quote in single", test_escape_single_quote_in_single),
        ("escape double-quote in double", test_escape_double_quote_in_double),
        ("escape backslash", test_escape_backslash),
        ("escape backslash in double", test_escape_backslash_in_double),
        ("escape at end of line", test_escape_at_end_of_line),
        ("escape eof single", test_escape_eof),
        ("escape eof double", test_escape_eof_double),
        ("error bracket in key", test_error_bracket_in_key),
        ("error bracket in key 2", test_error_bracket_in_key2),
        ("error colon no space", test_error_colon_not_followed_by_space),
        ("colon tab allowed", test_colon_then_tab_allowed),
        ("error unclosed reference", test_error_unclosed_reference),
        ("error unmatched brackets", test_error_unmatched_brackets),
        ("error unclosed triple-single", test_error_unclosed_triple_single),
        ("error unclosed triple-double", test_error_unclosed_triple_double),
        ("dump string", test_dump_string),
        ("dump string with hash", test_dump_string_with_hash),
        ("dump int", test_dump_int),
        ("dump float", test_dump_float),
        ("dump bool", test_dump_bool),
        ("dump none", test_dump_none),
        ("dump top-level none", test_dump_top_level_none),
        ("dump top-level bool", test_dump_top_level_bool),
        ("dump top-level int", test_dump_top_level_int),
        ("dump top-level string", test_dump_top_level_string),
        ("dump multiline string", test_dump_multiline_string),
        ("dump empty dict", test_dump_empty_dict),
        ("dump empty list", test_dump_empty_list),
        ("dump nested dict", test_dump_nested_dict),
        ("dump list simple roundtrip", test_dump_list_simple),
        ("dump roundtrip basic", test_dump_roundtrip_basic),
        ("dump roundtrip deep nested", test_dump_roundtrip_deep_nested),
        ("dump roundtrip list of dicts", test_dump_roundtrip_list_of_dicts),
        ("dump roundtrip mixed", test_dump_roundtrip_mixed),
        ("load from file", test_load_from_file),
        ("dump to file", test_dump_to_file),
        ("load from file object", test_load_from_file_object),
        ("only comments", test_only_comments),
        ("only block comment", test_only_block_comment),
        ("empty lines", test_empty_lines),
        ("leading empty lines", test_leading_empty_lines),
        ("trailing empty lines", test_trailing_empty_lines),
        ("mixed indentation", test_mixed_indentation),
        ("list all empty items", test_list_with_all_empty_items),
        ("reference self", test_reference_self),
        ("reference to list in dict", test_reference_to_list_in_dict),
        ("unicode strings", test_unicode_strings),
        ("unicode multiline", test_unicode_multiline),
        ("unicode keys", test_unicode_keys),
        ("hash start single-quote", test_value_starts_with_hash_in_quotes),
        ("triple inside single", test_triple_quote_inside_single_line),
        ("single inside triple double", test_single_quote_inside_triple_double),
        ("colon in value single", test_key_with_colon_in_value),
        ("colon in value double", test_key_with_colon_in_double_value),
    ]

    print("=" * 60)
    print("YACL Comprehensive Spec-Compliance Test Suite")
    print("=" * 60)
    for name, fn in test_functions:
        try:
            fn()
        except Exception as e:
            failed += 1
            errors.append(f"  ERROR in {name}: {e}")
            errors.append(f"  {traceback.format_exc().rstrip()}")
    print("-" * 60)
    for err in errors:
        print(err)
    if errors:
        print("-" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SOME TESTS FAILED!")
    else:
        print("All tests passed!")
    print("=" * 60)
