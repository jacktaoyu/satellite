# -*- coding: utf-8 -*-
"""鉴权逻辑单元自测（不启动 Flask 服务、不连接数据库、不影响运行中的后端进程）。

从 app.py 源码中用 ast 抽取 issue_token / check_token / parse_user_type /
global_auth_check 及 VALID_TOKENS 等定义，在隔离命名空间中执行并测试。
运行方式：cd backend && python3 test_auth_logic.py
"""
import ast
import os
import sys
from datetime import datetime, timedelta

SRC = os.path.join(os.path.dirname(__file__), 'app.py')
NEEDED_NAMES = {
    'VALID_TOKENS', 'TOKEN_LOCK', 'TOKEN_TTL_HOURS', 'AUTH_WHITELIST',
    'issue_token', 'check_token', 'parse_user_type', 'global_auth_check',
}

with open(SRC, 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read(), filename=SRC)

# 抽取目标定义（顶层赋值与函数定义），跳过会触发副作用的模块级代码（如 initialize_system()）
selected = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in NEEDED_NAMES:
        selected.append(node)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in NEEDED_NAMES:
                selected.append(node)
                break

found = set()
for node in selected:
    if isinstance(node, ast.FunctionDef):
        found.add(node.name)
    else:
        found.update(t.id for t in node.targets if isinstance(t, ast.Name))
missing = NEEDED_NAMES - found
assert not missing, f"app.py 中未找到以下定义: {missing}"

import secrets
import threading
from flask import Flask, request, jsonify

# 构造最小 Flask app，提供 before_request 装饰器所需的 request/jsonify 环境
mini_app = Flask(__name__)
ns = {
    'secrets': secrets, 'threading': threading, 'datetime': datetime,
    'timedelta': timedelta, 'request': request, 'jsonify': jsonify,
    'app': mini_app,
}
code = compile(ast.Module(body=selected, type_ignores=[]), SRC, 'exec')
exec(code, ns)

issue_token = ns['issue_token']
check_token = ns['check_token']
parse_user_type = ns['parse_user_type']
VALID_TOKENS = ns['VALID_TOKENS']
TOKEN_LOCK = ns['TOKEN_LOCK']

failures = []


def check(name, cond):
    print(('PASS' if cond else 'FAIL'), '-', name)
    if not cond:
        failures.append(name)


# ===== 1. token 签发与校验 =====
token = issue_token('alice')
check('issue_token 返回 32 位十六进制字符串', isinstance(token, str) and len(token) == 32)
check('token 已写入 VALID_TOKENS', token in VALID_TOKENS)
check('check_token 返回正确用户名', check_token(token) == 'alice')
check('未知 token 返回 None', check_token('0' * 32) is None)
check('空 token 返回 None', check_token(None) is None and check_token('') is None)

# ===== 2. 过期 token 被清除 =====
expired = issue_token('bob')
with TOKEN_LOCK:
    VALID_TOKENS[expired]['expiry'] = datetime.now() - timedelta(seconds=1)
check('过期 token 校验失败', check_token(expired) is None)
check('过期 token 被顺手清除', expired not in VALID_TOKENS)

# ===== 3. parse_user_type 容错 =====
check('parse_user_type("0") == 0', parse_user_type('0') == 0)
check('parse_user_type("1") == 1', parse_user_type('1') == 1)
check('parse_user_type(None) == 1', parse_user_type(None) == 1)
check('parse_user_type("abc") == 1（脏数据容错）', parse_user_type('abc') == 1)

# ===== 4. before_request 全局校验（用 Flask 测试请求上下文模拟） =====
# global_auth_check 已在 exec 时注册到 mini_app
@mini_app.route('/login/', methods=['POST'])
def _login():
    return 'ok'

@mini_app.route('/statistics')
def _statistics():
    return 'ok'

@mini_app.route('/getCurrentTime')
def _current_time():
    return 'ok'

@mini_app.route('/user/profile')
def _profile():
    return 'ok'

@mini_app.route('/static/image/x.png')
def _static():
    return 'ok'

client = mini_app.test_client()
valid = issue_token('carol')

r = client.post('/login/')
check('白名单 /login/ 无 token 放行', r.status_code == 200)
r = client.get('/statistics')
check('白名单 /statistics 无 token 放行', r.status_code == 200)
r = client.get('/getCurrentTime')
check('白名单 /getCurrentTime 无 token 放行', r.status_code == 200)
r = client.get('/static/image/x.png')
check('静态资源 /static/ 前缀放行', r.status_code == 200)
r = client.options('/user/profile')
check('OPTIONS 预检放行', r.status_code == 200)

r = client.get('/user/profile')
check('非白名单无 token 返回 401', r.status_code == 401)
check('401 响应体含 meta.status=401', r.get_json()['meta']['status'] == 401)
r = client.get('/user/profile', headers={'Ac-Token': 'f' * 32})
check('非法 token 返回 401', r.status_code == 401)
r = client.get('/user/profile', headers={'Ac-Token': valid})
check('有效 token 放行', r.status_code == 200)

expired2 = issue_token('dave')
with TOKEN_LOCK:
    VALID_TOKENS[expired2]['expiry'] = datetime.now() - timedelta(hours=1)
r = client.get('/user/profile', headers={'Ac-Token': expired2})
check('过期 token 返回 401', r.status_code == 401)

print()
if failures:
    print(f'共 {len(failures)} 项失败: {failures}')
    sys.exit(1)
print('全部测试通过')
