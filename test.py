import yacl
import os
import tempfile
import textwrap


def _print_value(name, actual):
    """只打印实际解析值"""
    print(f"  {name}: {repr(actual)}")
    print()

def _print_config(config):
    """打印配置原文"""
    print("📄 配置内容:")
    print("```")
    print(config.strip())
    print("```")
    print()

# ------------------- 测试用例 -------------------
def test_basic_types():
    config = textwrap.dedent("""
        aaa: 'hello world'
        bbb: "hello #world"
        ccc: 42
        ddd: 3.14
        eee: true
        fff: on
        ggg: enabled
        hhh: false
        iii: off
        jjj: disabled
        kkk: none
    """)
    print("\n=== 基本数据类型测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("aaa", result.get('aaa'))
    _print_value("bbb", result.get('bbb'))
    _print_value("ccc", result.get('ccc'))
    _print_value("ddd", result.get('ddd'))
    _print_value("eee", result.get('eee'))
    _print_value("fff", result.get('fff'))
    _print_value("ggg", result.get('ggg'))
    _print_value("hhh", result.get('hhh'))
    _print_value("iii", result.get('iii'))
    _print_value("jjj", result.get('jjj'))
    _print_value("kkk", result.get('kkk'))

def test_multiline_strings():
    config = textwrap.dedent("""
        single: 
          '''
        多行文本1
        多行文本2
        多行文本3
        '''

        double: 
          '''
        多行文本1 #注释行会被忽略
        多行文本2
        多行文本3
        '''

        inline_single: '''单行
        多行'''

        inline_single2: '''
        单行
        多行'''
    """)
    print("\n=== 多行字符串测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("single", result.get('single'))
    _print_value("double", result.get('double'))
    _print_value("inline_single", result.get('inline_single'))
    _print_value("inline_single2", result.get('inline_single2'))

def test_lists():
    config = textwrap.dedent("""
        simple_list: 
          - 1
          - 2
          - 3
          - 'hello world'
          - true
          - none

        nested_list: 
          - 
            - 'a'
            - 'b'
            - 'c'
          - 
            - 'd'
            - 'e'
            - 'f'

        list_with_dict:
          - 1: 'first'
          - 2: 'second'
          - 3: 'third'
    """)
    print("\n=== 列表测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("simple_list", result.get('simple_list'))
    _print_value("nested_list", result.get('nested_list'))
    _print_value("list_with_dict", result.get('list_with_dict'))

def test_nested_objects():
    config = textwrap.dedent("""
        root:
          level1:
            level2:
              level3: 'deep value'
              number: 42
            other: 'other value'
          another: 'top level'
    """)
    print("\n=== 嵌套对象测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    root = result.get('root', {})
    level1 = root.get('level1', {})
    level2 = level1.get('level2', {})
    _print_value("level3", level2.get('level3'))
    _print_value("number", level2.get('number'))
    _print_value("other", level1.get('other'))
    _print_value("another", root.get('another'))

def test_references():
    config = textwrap.dedent("""
        ppp:
          qqq:
            rrr: 'abc'
        sss: [ppp].[qqq].[rrr]

        xxx:
          - 1:
              - 'a'
              - 'b'
          - 2:
              - 'c'
              - 'd'
        yyy: [xxx].0.[1].0

        1:
          2:
            3: 'hhh'
        www: [1].[2].[3]
    """)
    print("\n=== 引用测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("sss", result.get('sss'))
    _print_value("yyy", result.get('yyy'))
    _print_value("www", result.get('www'))

def test_reference_edge_cases():
    config = textwrap.dedent("""
        a:
          b: 'value'
        ref1: [a].[b]
        ref2: [a].[c]
        ref3: [a].0
        ref4: [missing].key
    """)
    print("\n=== 引用边界测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("ref1", result.get('ref1'))
    _print_value("ref2", result.get('ref2'))
    _print_value("ref3", result.get('ref3'))
    _print_value("ref4", result.get('ref4'))

def test_complex_config():
    config = textwrap.dedent("""
        database:
          host: 'localhost'
          port: 5432
          credentials:
            username: 'admin'
            password: 'secret123'
          pools:
            - 1
            - 2
            - 3

        server:
          enabled: true
          endpoints:
            - '/api/v1'
            - '/api/v2'
            - '/api/v3'
          timeout: 30.5

        features:
          - name: 'auth'
            enabled: true
            config:
              token_expiry: 3600
          - name: 'logging'
            enabled: on
            config:
              level: 'debug'
              file: '/var/log/app.log'

        none_value: none
    """)
    print("\n=== 复杂配置测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    db = result.get('database')
    _print_value("database.host", db.get('host'))
    _print_value("database.port", db.get('port'))
    _print_value("database.credentials.username", db['credentials']['username'])
    _print_value("database.pools", db['pools'])
    server = result.get('server')
    _print_value("server.enabled", server.get('enabled'))
    _print_value("server.endpoints", server['endpoints'])
    features = result.get('features')
    _print_value("features[0].name", features[0]['name'])
    _print_value("features[1].config.level", features[1]['config']['level'])
    _print_value("none_value", result.get('none_value'))

def test_string_escaping():
    config = textwrap.dedent("""
        with_hash: 'This is #not a comment'
        with_quote: "He said: \\"Hello\\" #this is a comment"
        single_quote: 'Don\\'t worry'
    """)
    print("\n=== 字符串转义测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("with_hash", result.get('with_hash'))
    _print_value("with_quote", result.get('with_quote'))
    _print_value("single_quote", result.get('single_quote'))

def test_comments_and_block_comments():
    config = textwrap.dedent("""
        # 这是行注释
        key1: 'visible'
        ### 块注释开始
        key2: 'should be ignored'
        ### 块注释结束
        key3: 'visible again'

        # 嵌套块注释
        ### outer
        key4: 'ignored'
          ### inner
          key5: 'also ignored'
          ### inner end
        ### outer end
        key6: 'visible'
    """)
    print("\n=== 注释测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("key1", result.get('key1'))
    _print_value("key2", result.get('key2'))
    _print_value("key3", result.get('key3'))
    _print_value("key4", result.get('key4'))
    _print_value("key5", result.get('key5'))
    _print_value("key6", result.get('key6'))

def test_empty_and_missing_values():
    config = textwrap.dedent("""
        empty_dict:
        empty_list: 
          - 
        empty_scalar: 
        key_without_value:
    """)
    print("\n=== 空值测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("empty_dict", result.get('empty_dict'))
    _print_value("empty_list", result.get('empty_list'))
    _print_value("empty_scalar", result.get('empty_scalar'))
    _print_value("key_without_value", result.get('key_without_value'))

def test_list_with_mixed_types():
    config = textwrap.dedent("""
        data:
          - 1
          - 'string'
          - true
          - none
          - 
            subkey: 'subvalue'
          - 
            - nested1
            - nested2
          - [data].0
    """)
    print("\n=== 混合列表测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    data = result.get('data')
    _print_value("data[0]", data[0])
    _print_value("data[1]", data[1])
    _print_value("data[2]", data[2])
    _print_value("data[3]", data[3])
    _print_value("data[4]", data[4])
    _print_value("data[5]", data[5])
    _print_value("data[6]", data[6])

def test_invalid_configs():
    print("\n=== 无效配置测试（预期抛出异常） ===")
    config_bad1 = textwrap.dedent("""
        bad: '''unclosed
    """)
    print("📄 配置1（未闭合单引号三引号）:")
    print("```")
    print(config_bad1.strip())
    print("```\n")
    try:
        yacl.loads(config_bad1)
        print("  ❌ 未捕获异常")
    except yacl.YACLParseError:
        print("  ✅ 正确捕获 YACLParseError")
    except Exception as e:
        print(f"  ⚠️ 捕获到其他异常: {e}")

    config_bad2 = textwrap.dedent('''
        bad: """unclosed
    ''')
    print("📄 配置2（未闭合双引号三引号）:")
    print("```")
    print(config_bad2.strip())
    print("```\n")
    try:
        yacl.loads(config_bad2)
        print("  ❌ 未捕获异常")
    except yacl.YACLParseError:
        print("  ✅ 正确捕获 YACLParseError")
    except Exception as e:
        print(f"  ⚠️ 捕获到其他异常: {e}")

    config_bad3 = textwrap.dedent("""
        ref: [a].[b
    """)
    print("📄 配置3（无效引用语法）:")
    print("```")
    print(config_bad3.strip())
    print("```\n")
    try:
        yacl.loads(config_bad3)
        print("  ❌ 未捕获异常")
    except yacl.YACLParseError:
        print("  ✅ 正确捕获 YACLParseError")
    except Exception as e:
        print(f"  ⚠️ 捕获到其他异常: {e}")

def test_dump_and_reload():
    original = {
        "name": "test",
        "age": 30,
        "active": True,
        "metadata": {"created": "2024-01-01", "tags": ["python", "yaml", "config"]},
        "items": [{"id": 1, "value": "first"}, {"id": 2, "value": "second"}]
    }
    print("\n=== dump/load 往返测试 ===")
    print("📄 原始数据结构（将被序列化）:")
    print(original)
    print()
    dumped = yacl.dumps(original, indent=2)
    print("📄 序列化后的 YACL 文本:")
    print("```")
    print(dumped)
    print("```\n")
    reloaded = yacl.loads(dumped)
    _print_value("重新加载后的数据", reloaded)

def test_file_operations():
    config = textwrap.dedent("""
        test_file: 'loaded from file'
        number: 42
    """)
    print("\n=== 文件操作测试 ===")
    _print_config(config)
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.yacl', delete=False) as f:
        f.write(config)
        tmp_path = f.name

    try:
        result = yacl.load(tmp_path)
        _print_value("test_file", result.get('test_file'))
        _print_value("number", result.get('number'))

        data_to_dump = {"key": "value"}
        print("📄 将要 dump 到文件的数据:", data_to_dump)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            yacl.dump(data_to_dump, f)
        reloaded = yacl.load(tmp_path)
        _print_value("dump后重新加载", reloaded)
    finally:
        os.unlink(tmp_path)

def test_yacl_specific_features():
    config = textwrap.dedent("""
        unclosed: 'this spans
        multiple lines
        with no ending quote'

        indented: '''
            first line indented 4
                second line indented 8
            third line indented 4
        '''

        mixed_refs:
          - [unclosed]
          - [indented]
          - 'literal'
    """)
    print("\n=== YACL 特色功能测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("unclosed", result.get('unclosed'))
    _print_value("indented", result.get('indented'))
    refs = result.get('mixed_refs')
    _print_value("mixed_refs[0]", refs[0])
    _print_value("mixed_refs[1]", refs[1])
    _print_value("mixed_refs[2]", refs[2])

def test_numeric_keys():
    config = textwrap.dedent("""
        1: 'value1'
        2:
          3: 'value2'
        ref: [1]
        ref2: [2].[3]
    """)
    print("\n=== 数字键测试 ===")
    _print_config(config)
    result = yacl.loads(config)
    _print_value("1", result.get('1'))
    _print_value("2.3", result.get('2').get('3'))
    _print_value("ref", result.get('ref'))
    _print_value("ref2", result.get('ref2'))

def test_load_from_file_object():
    print("\n=== 从文件对象加载测试 ===")
    config = "test_key: 'from file object'"
    print("📄 配置内容:")
    print(f"```\n{config}\n```\n")
    
    from io import StringIO
    file_obj = StringIO(config)
    result = yacl.load(file_obj)
    _print_value("test_key", result.get('test_key'))

# ------------------- 运行所有测试 -------------------
if __name__ == "__main__":
    tests = [
        test_basic_types,
        test_multiline_strings,
        test_lists,
        test_nested_objects,
        test_references,
        test_reference_edge_cases,
        test_complex_config,
        test_string_escaping,
        test_comments_and_block_comments,
        test_empty_and_missing_values,
        test_list_with_mixed_types,
        test_invalid_configs,
        test_dump_and_reload,
        test_file_operations,
        test_yacl_specific_features,
        test_numeric_keys,
        test_load_from_file_object,
    ]
    print("=" * 70)
    print("YACL 解析器测试套件（显示配置与实际解析结果）")
    print("=" * 70)
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"\n⚠️ 测试 {t.__name__} 发生未预期异常: {e}")
            import traceback
            traceback.print_exc()
        print("-" * 70)
    print("\n所有测试执行完毕，请根据配置手动核对解析结果。")