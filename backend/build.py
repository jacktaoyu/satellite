import PyInstaller.__main__
import os
import sys
from pathlib import Path

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义需要包含的数据文件
datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('blueprint', 'blueprint'),
    ('model', 'model'),
    ('Service', 'Service'),
    ('utils', 'utils'),
]

# 构建 --add-data 参数
add_data_args = []
for src, dst in datas:
    src_path = os.path.join(current_dir, src)
    if os.path.exists(src_path):
        add_data_args.extend(['--add-data', f'{src_path};{dst}'])

# 定义需要包含的隐藏导入
hidden_imports = [
    'flask',
    'flask.json',
    'flask.templating',
    'flask.views',
    'flask.blueprints',
    'werkzeug',
    'werkzeug.routing',
    'werkzeug.middleware',
    'werkzeug.wrappers',
    'jinja2',
    'jinja2.ext',
    'itsdangerous',
    'click',
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.sql',
    'pandas',
    'openpyxl',
    'extions',
]

# 构建 --hidden-import 参数
hidden_import_args = []
for imp in hidden_imports:
    hidden_import_args.extend(['--hidden-import', imp])

# 获取 Python 安装路径
python_path = os.path.dirname(sys.executable)
site_packages = os.path.join(python_path, 'Lib', 'site-packages')

# 构建完整的 PyInstaller 命令
PyInstaller.__main__.run([
    'app.py',
    '--onefile',
    '--clean',
    '--name', 'satellite_system',
    '--paths', current_dir,
    '--paths', site_packages,
    *hidden_import_args,
    *add_data_args,
    '--collect-all', 'flask',
    '--collect-all', 'werkzeug',
    '--collect-all', 'jinja2',
    '--collect-all', 'sqlalchemy',
    '--collect-all', 'pandas',
    '--collect-all', 'openpyxl',
    '--collect-all', 'extions',
    '--debug', 'all',
]) 