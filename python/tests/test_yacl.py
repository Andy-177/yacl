# -*- coding: utf-8 -*-
"""Test suite for the pure Python YACL implementation."""

import io
import json
import os
import sys
import unittest

# Make ``import yacl`` work no matter which directory the tests are run from.
# Set YACL_PATH to test a specific implementation directory, e.g.
# ``YACL_PATH=pymodule`` to test the generated package.
_impl = os.environ.get("YACL_PATH")
if _impl:
    sys.path.insert(0, os.path.abspath(_impl))
else:
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

import yacl


class TestScalars(unittest.TestCase):
    def test_basic_types(self):
        text = "\n".join(
            [
                "姓名: '张三",
                "年龄: 30",
                "身高: 1.75",
                "激活: true",
                "角色: none",
                "关: false",
                "o: on",
                "off_: off",
                "en: enabled",
                "dis: disabled",
                "负: -456",
                "科学: 1e3",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "姓名": "张三",
                "年龄": 30,
                "身高": 1.75,
                "激活": True,
                "角色": None,
                "关": False,
                "o": True,
                "off_": False,
                "en": True,
                "dis": False,
                "负": -456,
                "科学": 1000.0,
            },
        )

    def test_single_quoted_is_literal_to_eol(self):
        text = "a: 'x # y'\nb: 'no end"
        self.assertEqual(yacl.loads(text), {"a": "x # y'", "b": "no end"})

    def test_double_quoted_stops_at_hash(self):
        text = 'a: "hello # comment'
        self.assertEqual(yacl.loads(text), {"a": "hello"})

    def test_case_sensitive_booleans(self):
        text = "a: True\nb: FALSE\nc: Yes"
        self.assertEqual(yacl.loads(text), {"a": "True", "b": "FALSE", "c": "Yes"})

    def test_empty_value_is_none(self):
        self.assertEqual(yacl.loads("a:\nb: 1"), {"a": None, "b": 1})

    def test_inline_empty_collections(self):
        self.assertEqual(yacl.loads("a: []\nb: {}"), {"a": [], "b": {}})

    def test_tabs_and_crlf(self):
        self.assertEqual(yacl.loads("a:\n\tb: 1\n\tc:\n\t\t- 2"), {"a": {"b": 1, "c": [2]}})
        self.assertEqual(yacl.loads("a: 1\r\nb:\r\n    - 2\r\n"), {"a": 1, "b": [2]})


class TestStructures(unittest.TestCase):
    def test_nested_objects(self):
        text = "\n".join(
            [
                "配置:",
                "    超时: 30",
                "    重试次数: 3",
                "    服务器:",
                "        主机: 'localhost",
                "        端口: 8080",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "配置": {
                    "超时": 30,
                    "重试次数": 3,
                    "服务器": {"主机": "localhost", "端口": 8080},
                }
            },
        )

    def test_list_of_scalars(self):
        text = "水果:\n    - '苹果\n    - '香蕉\n    - 3"
        self.assertEqual(yacl.loads(text), {"水果": ["苹果", "香蕉", 3]})

    def test_list_item_object_first_key_on_dash(self):
        text = "\n".join(
            [
                "服务:",
                "    - 名称: 'api",
                "      端口: 8080",
                "      白名单:",
                "          - '10.0.0.1",
                "          - '10.0.0.2",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "服务": [
                    {
                        "名称": "api",
                        "端口": 8080,
                        "白名单": ["10.0.0.1", "10.0.0.2"],
                    }
                ]
            },
        )

    def test_dash_alone_then_object(self):
        text = "\n".join(
            [
                "服务2:",
                "    -",
                "        名称: 'api",
                "        端口: 8080",
            ]
        )
        self.assertEqual(
            yacl.loads(text), {"服务2": [{"名称": "api", "端口": 8080}]}
        )

    def test_level2_object_item(self):
        text = "level1:\n    - level2:\n        - hello"
        self.assertEqual(
            yacl.loads(text), {"level1": [{"level2": ["hello"]}]}
        )

    def test_sub_list(self):
        text = "\n".join(
            [
                "矩阵:",
                "    -",
                "        - 1",
                "        - 2",
                "        - 3",
                "    -",
                "        - 4",
                "        - 5",
                "        - 6",
            ]
        )
        self.assertEqual(yacl.loads(text), {"矩阵": [[1, 2, 3], [4, 5, 6]]})

    def test_single_element_list_vs_siblings(self):
        single = "单元素:\n    -\n        - 1\n        - 2\n        - 3"
        sib = "三个元素:\n    - 1\n    - 2\n    - 3"
        self.assertEqual(yacl.loads(single), {"单元素": [[1, 2, 3]]})
        self.assertEqual(yacl.loads(sib), {"三个元素": [1, 2, 3]})

    def test_deep_nesting(self):
        text = "\n".join(
            [
                "组织:",
                "    - 名称: '研发部",
                "      小组:",
                "          - 名称: '前端",
                "            成员:",
                "                - 'Alice",
                "                - 'Bob",
                "          - 名称: '后端",
                "            成员:",
                "                - 'Carol",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "组织": [
                    {
                        "名称": "研发部",
                        "小组": [
                            {"名称": "前端", "成员": ["Alice", "Bob"]},
                            {"名称": "后端", "成员": ["Carol"]},
                        ],
                    }
                ]
            },
        )

    def test_mixed_matrix(self):
        text = "\n".join(
            [
                "矩阵:",
                "    -",
                "        - 1",
                "        - '二",
                "        - 3.0",
                "    -",
                "        - 4",
                "        - 5",
                "        - '六",
            ]
        )
        self.assertEqual(
            yacl.loads(text), {"矩阵": [[1, "二", 3.0], [4, 5, "六"]]}
        )


class TestReferences(unittest.TestCase):
    def test_basic_references(self):
        text = "\n".join(
            [
                "人员:",
                "    姓名: 'Alice",
                "    年龄: 30",
                "    爱好:",
                "        - '阅读",
                "        - '游戏",
                "人员姓名: [人员].[姓名]",
                "第一个爱好: [人员].[爱好].0",
                "第二个爱好: [人员].[爱好].[1]",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "人员": {"姓名": "Alice", "年龄": 30, "爱好": ["阅读", "游戏"]},
                "人员姓名": "Alice",
                "第一个爱好": "阅读",
                "第二个爱好": "游戏",
            },
        )

    def test_reference_through_list_of_objects(self):
        text = "\n".join(
            [
                "服务:",
                "    - 名称: 'api",
                "      白名单:",
                "          - '10.0.0.1",
                "首个白名单: [服务].0.[白名单].0",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {
                "服务": [{"名称": "api", "白名单": ["10.0.0.1"]}],
                "首个白名单": "10.0.0.1",
            },
        )

    def test_nested_reference_inside_object(self):
        text = "\n".join(
            [
                "人员:",
                "    姓名: 'Alice",
                "    别名: [姓名]",
            ]
        )
        self.assertEqual(
            yacl.loads(text), {"人员": {"姓名": "Alice", "别名": "Alice"}}
        )

    def test_missing_reference_is_none(self):
        self.assertIsNone(yacl.loads("a: [不存在]")["a"])


class TestComments(unittest.TestCase):
    def test_line_comments(self):
        text = "\n".join(
            [
                "# 这是注释",
                "值: 42   # 行内注释",
                "含井号的字符串: '这个 # 不是注释",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {"值": 42, "含井号的字符串": "这个 # 不是注释"},
        )

    def test_multiline_comment_readme_style(self):
        text = "\n".join(
            [
                "# 这是注释",
                "值: 42   # 行内注释",
                "",
                "###",
                "这是多行注释。",
                "可以包含 # 等特殊字符。",
                "以另一个 ### 结束",
                "###",
                "",
                "含井号的字符串: '这个 # 不是注释",
            ]
        )
        self.assertEqual(
            yacl.loads(text),
            {"值": 42, "含井号的字符串": "这个 # 不是注释"},
        )

    def test_inline_multiline_comment(self):
        text = "a: 1 ### comment ###   \nb: 2"
        self.assertEqual(yacl.loads(text), {"a": 1, "b": 2})

    def test_comment_inside_nested_block(self):
        text = "\n".join(
            [
                "outer:",
                "    ###",
                "    comment",
                "    ###",
                "    a: 1",
            ]
        )
        self.assertEqual(yacl.loads(text), {"outer": {"a": 1}})

    def test_hash_block_inside_list(self):
        text = "a:\n    - 1\n    ###\n    comment\n    ###\n    - 2"
        self.assertEqual(yacl.loads(text), {"a": [1, 2]})

    def test_inline_hash_comment_in_object_item(self):
        text = "a:\n    - b: 1 ### c ###\n      d: 2"
        self.assertEqual(yacl.loads(text), {"a": [{"b": 1, "d": 2}]})


class TestMultilineStrings(unittest.TestCase):
    def test_triple_single_equivalence(self):
        self.assertEqual(yacl.loads("x: '''\naaa\nbbb\n'''"), {"x": "aaa\nbbb"})
        self.assertEqual(yacl.loads("y: '''aaa\nbbb\n'''"), {"y": "aaa\nbbb"})
        self.assertEqual(yacl.loads("z: '''\naaa\nbbb'''"), {"z": "aaa\nbbb"})
        self.assertEqual(yacl.loads("w: '''aaa\nbbb'''"), {"w": "aaa\nbbb"})

    def test_triple_single_keeps_hash(self):
        text = "c: '''\n多行\n包含 # 号\n'''"
        self.assertEqual(yacl.loads(text), {"c": "多行\n包含 # 号"})

    def test_triple_double_strips_hash(self):
        text = 'd: """\n这一行保留\n配置: # 移除\n这一行也保留\n"""'
        self.assertEqual(yacl.loads(text), {"d": "这一行保留\n配置: \n这一行也保留"})

    def test_triple_with_leading_and_trailing_newlines(self):
        # One leading / trailing newline next to a delimiter is trimmed.
        self.assertEqual(yacl.loads("a: '''\n\nx\n\n'''"), {"a": "\nx\n"})
        self.assertEqual(yacl.loads("a: '''x\n'''"), {"a": "x"})
        # An extra blank line preserves one newline.
        self.assertEqual(yacl.loads("a: '''x\n\n'''"), {"a": "x\n"})


class TestBlockScalars(unittest.TestCase):
    def test_pipe_indented(self):
        text = "\n".join(
            [
                "level1:",
                "    text1: |",
                "        我是第一行文本",
                "        我是第二行",
                "        # 我是注释",
                "            我是第四行",
                "    tips: '同级",
            ]
        )
        self.assertEqual(
            yacl.loads(text)["level1"]["text1"],
            "我是第一行文本\n我是第二行\n# 我是注释\n    我是第四行",
        )
        self.assertEqual(yacl.loads(text)["level1"]["tips"], "同级")

    def test_double_pipe_indented(self):
        text = "\n".join(
            [
                "level1:",
                "    text2: ||",
                "        我是第一行文本",
                "        配置: value # 移除",
                "        key: '字面",
                "    key: '真正的键",
            ]
        )
        self.assertEqual(
            yacl.loads(text)["level1"]["text2"],
            "我是第一行文本\n配置: value \nkey: '字面",
        )
        self.assertEqual(yacl.loads(text)["level1"]["key"], "真正的键")

    def test_pipe_with_line_count(self):
        text = "\n".join(
            [
                "level2:",
                "    text1: |3",
                "我是第一行文本",
                "# 我是注释",
                "     我是第三行",
                "    text2: '同级",
            ]
        )
        self.assertEqual(
            yacl.loads(text)["level2"]["text1"],
            "我是第一行文本\n# 我是注释\n     我是第三行",
        )
        self.assertEqual(yacl.loads(text)["level2"]["text2"], "同级")

    def test_double_pipe_with_line_count(self):
        text = "\n".join(
            [
                "level2:",
                "    text2: ||3",
                "我是第一行文本",
                "配置: debug # 注释",
                "我是第二行文本",
                "# 整行注释",
                "    key: '同级",
            ]
        )
        self.assertEqual(
            yacl.loads(text)["level2"]["text2"],
            "我是第一行文本\n配置: debug \n我是第二行文本",
        )
        self.assertEqual(yacl.loads(text)["level2"]["key"], "同级")

    def test_blank_lines_preserved(self):
        text = "a: |\n    x\n\n    y\nb: 1"
        self.assertEqual(yacl.loads(text)["a"], "x\n\ny")


class TestLoadDump(unittest.TestCase):
    def test_load_from_file_object(self):
        data = yacl.load(io.StringIO("a: 1\nb: 'x"))
        self.assertEqual(data, {"a": 1, "b": "x"})

    def test_dumps_scalars(self):
        self.assertEqual(yacl.dumps(None), "none")
        self.assertEqual(yacl.dumps(True), "true")
        self.assertEqual(yacl.dumps(False), "false")
        self.assertEqual(yacl.dumps(42), "42")
        self.assertEqual(yacl.dumps(1.5), "1.5")
        self.assertEqual(yacl.dumps("hi"), "'hi")
        self.assertEqual(yacl.dumps(""), "'")
        self.assertEqual(yacl.dumps("a # b"), "'a # b")

    def test_dumps_multiline_scalar_roundtrip(self):
        for value in [
            "line1\nline2",
            "a\n",
            "\na",
            "'''triple",
            "a'''b\nc",
            "x\n\ny",
        ]:
            self.assertEqual(yacl.loads(yacl.dumps(value)), value)

    def test_dumps_and_loads_roundtrip(self):
        data = {
            "名称": "MyApp",
            "端口": 8080,
            "调试": True,
            "空": None,
            "列表": [1, 2.5, "三", False, None],
            "嵌套": {"a": [1, 2], "b": {"c": "d"}},
            "对象列表": [{"x": 1, "y": [2, 3]}, {"z": "最后"}],
            "矩阵": [[1, 2], [3, 4]],
            "多行": "line1\nline2\nline3",
            "多行尾换行": "a\n",
            "多行首换行": "\na",
            "含三引号": "a'''b\nc",
            "空列表": [],
            "空对象": {},
            "井号": "a # not comment",
            "引号": "it's",
        }
        text = yacl.dumps(data)
        self.assertEqual(yacl.loads(text), data)

    def test_dumps_empty_collections(self):
        self.assertEqual(yacl.dumps({}), "{}")
        self.assertEqual(yacl.dumps([]), "[]")
        self.assertEqual(yacl.dumps({"a": [], "b": {}}), "a: []\nb: {}")

    def test_dumps_indent_option(self):
        text = yacl.dumps({"a": {"b": 1}}, indent=2)
        self.assertEqual(text, "a:\n  b: 1")

    def test_dumps_sort_keys(self):
        text = yacl.dumps({"b": 1, "a": 2}, sort_keys=True)
        self.assertEqual(text, "a: 2\nb: 1")

    def test_dump_to_file_object(self):
        fp = io.StringIO()
        yacl.dump({"a": [1, 2]}, fp)
        self.assertEqual(fp.getvalue(), "a:\n    - 1\n    - 2")

    def test_default_hook(self):
        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        data = {"p": Point(1, 2)}
        text = yacl.dumps(data, default=lambda o: {"x": o.x, "y": o.y})
        self.assertEqual(yacl.loads(text), {"p": {"x": 1, "y": 2}})

    def test_nested_list_of_objects_roundtrip(self):
        data = {"a": [{"b": [1, 2], "c": 3}, {"d": {"e": "f"}}]}
        self.assertEqual(yacl.loads(yacl.dumps(data)), data)

    def test_nested_lists_roundtrip(self):
        data = {"m": [[1, 2], [3, [4, 5]]]}
        self.assertEqual(yacl.loads(yacl.dumps(data)), data)

    def test_parse_int_float_hooks(self):
        data = yacl.loads("a: 10\nb: 1.5", parse_int=lambda s: int(s) * 2)
        self.assertEqual(data["a"], 20)

    def test_object_pairs_hook(self):
        data = yacl.loads("a: 1\nb: 2", object_pairs_hook=dict)
        self.assertEqual(data, {"a": 1, "b": 2})


class TestTopLevel(unittest.TestCase):
    def test_top_level_scalar(self):
        self.assertEqual(yacl.loads("42"), 42)
        self.assertEqual(yacl.loads("'hello"), "hello")
        self.assertEqual(yacl.loads("true"), True)
        self.assertEqual(yacl.loads("none"), None)

    def test_top_level_list(self):
        self.assertEqual(yacl.loads("- 1\n- 2"), [1, 2])

    def test_tuple_serialization(self):
        self.assertEqual(yacl.dumps((1, 2)), "- 1\n- 2")
        self.assertEqual(yacl.dumps({"a": (1, 2)}), "a:\n    - 1\n    - 2")


class TestErrors(unittest.TestCase):
    def test_unterminated_triple(self):
        with self.assertRaises(yacl.YACLDecodeError):
            yacl.loads("a: '''\nfoo")

    def test_unexpected_indent(self):
        with self.assertRaises(yacl.YACLDecodeError):
            yacl.loads("a: 1\n    b: 2")

    def test_bad_input_type(self):
        with self.assertRaises(TypeError):
            yacl.loads(123)

    def test_decode_error_attributes(self):
        try:
            yacl.loads("a: 1\n   b")
        except yacl.YACLDecodeError as exc:
            self.assertGreater(exc.lineno, 0)
            self.assertGreater(exc.colno, 0)


class TestReadmeFullExample(unittest.TestCase):
    def test_block_scalar_examples(self):
        text = "\n".join(
            [
                "日志配置: |",
                "    # 日志级别",
                "    level: INFO",
                "    # 输出格式",
                "    format: json",
                "    保留这些配置行",
                "",
                "代码片段: ||",
                "    def hello():",
                "        # 打印问候",
                '        print("Hello")',
                "        # 返回结果",
                "        return True",
                "",
                "示例文本: |4",
                "第一行",
                "# 这是注释，被保留",
                "第二行",
                "第三行",
                "# 这行超出指定行数，不包含",
            ]
        )
        data = yacl.loads(text)
        self.assertEqual(
            data["日志配置"],
            "# 日志级别\nlevel: INFO\n# 输出格式\nformat: json\n保留这些配置行",
        )
        self.assertEqual(
            data["代码片段"],
            'def hello():\n    \n    print("Hello")\n    \n    return True',
        )
        self.assertEqual(
            data["示例文本"], "第一行\n# 这是注释，被保留\n第二行\n第三行"
        )

    def test_full_example(self):
        text = "\n".join(
            [
                "# 应用设置",
                "应用:",
                "    名称: 'MyApp",
                "    版本: 1.0.0",
                "    调试模式: enabled",
                "",
                "数据库:",
                "    主机: 'localhost",
                "    端口: 5432",
                "    凭证:",
                "        用户: 'admin",
                "        密码: 'secret",
                "",
                "功能:",
                "    - '身份验证",
                "    - '日志",
                "    - '分析",
                "",
                "默认功能: [功能].0",
                "",
                "矩阵:",
                "    -",
                "        - 1",
                "        - '二",
                "        - 3.0",
                "    -",
                "        - 4",
                "        - 5",
                "        - '六",
                "",
                "服务:",
                "    - 名称: 'api",
                "      端口: 8080",
                "      白名单:",
                "          - '10.0.0.1",
                "          - '10.0.0.2",
                "    - 名称: 'worker",
                "      端口: 8081",
                "      白名单:",
                "          - '10.0.0.3",
                "",
                "首个白名单: [服务].0.[白名单].0",
                "",
                "服务2:",
                "    -",
                "        名称: 'api",
                "        端口: 8080",
                "        白名单:",
                "            - '10.0.0.1",
                "            - '10.0.0.2",
            ]
        )
        data = yacl.loads(text)
        self.assertEqual(data["应用"]["名称"], "MyApp")
        self.assertEqual(data["应用"]["版本"], "1.0.0")
        self.assertEqual(data["应用"]["调试模式"], True)
        self.assertEqual(data["默认功能"], "身份验证")
        self.assertEqual(data["矩阵"], [[1, "二", 3.0], [4, 5, "六"]])
        self.assertEqual(data["首个白名单"], "10.0.0.1")
        self.assertEqual(data["服务"][1]["名称"], "worker")
        self.assertEqual(
            data["服务2"],
            [{"名称": "api", "端口": 8080, "白名单": ["10.0.0.1", "10.0.0.2"]}],
        )


if __name__ == "__main__":
    unittest.main()