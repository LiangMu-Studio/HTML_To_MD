"""根据白名单生成排除模块列表"""
import subprocess
import sys

# 实际需要的依赖（白名单）
REQUIRED_PACKAGES = {
    'PyQt5', 'requests', 'beautifulsoup4', 'lxml', 'fpdf2',
    'python-docx', 'readability-lxml', 'DrissionPage', 'pywin32',
    'PyInstaller',
    # 这些包的实际导入名
    'bs4', 'docx', 'readability', 'fpdf', 'win32api', 'win32com',
    # requests 的依赖
    'urllib3', 'certifi', 'charset-normalizer', 'idna',
    # beautifulsoup4 的依赖
    'soupsieve',
    # DrissionPage 的依赖
    'websocket', 'websocket-client', 'tldextract', 'requests-file', 'filelock',
    # lxml 相关
    'cssselect',
    # python-docx 的依赖
    'openpyxl',
    # PyInstaller 相关
    'altgraph', 'pyinstaller-hooks-contrib', 'pefile', 'pywin32-ctypes',
}

# 标准库（不需要排除）
STDLIB = {
    'os', 'sys', 're', 'json', 'pathlib', 'typing', 'html', 'urllib',
    'base64', 'shutil', 'tempfile', 'time', 'argparse', 'concurrent',
    'collections', 'functools', 'itertools', 'copy', 'io', 'hashlib',
    'subprocess', 'threading', 'multiprocessing', 'queue', 'socket',
    'ssl', 'email', 'http', 'xml', 'logging', 'warnings', 'traceback',
    'inspect', 'abc', 'contextlib', 'dataclasses', 'enum', 'string',
    'textwrap', 'unicodedata', 'codecs', 'locale', 'gettext',
    'struct', 'ctypes', 'platform', 'sysconfig', 'importlib',
    'pkgutil', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',
    'csv', 'configparser', 'pickle', 'shelve', 'sqlite3',
    'datetime', 'calendar', 'random', 'statistics', 'math', 'decimal',
    'fractions', 'numbers', 'cmath', 'operator', 'weakref', 'gc',
    'winreg', 'msvcrt', 'mmap', 'signal', 'errno', 'stat', 'glob',
    'fnmatch', 'linecache', 'tokenize', 'keyword', 'token', 'ast',
    'dis', 'code', 'codeop', 'pprint', 'reprlib', 'difflib',
    'unittest', 'doctest', 'pdb', 'profile', 'timeit', 'trace',
    'atexit', 'builtins', 'types', 'copy', 'pprint', 'graphlib',
}

def get_installed_packages():
    """获取当前环境安装的所有包"""
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
        capture_output=True, text=True
    )
    packages = set()
    for line in result.stdout.strip().split('\n'):
        if '==' in line:
            pkg = line.split('==')[0].lower()
            packages.add(pkg)
    return packages

def generate_excludes():
    """生成排除列表"""
    installed = get_installed_packages()
    required_lower = {p.lower() for p in REQUIRED_PACKAGES}

    excludes = []
    for pkg in installed:
        if pkg.lower() not in required_lower and pkg not in STDLIB:
            excludes.append(pkg)

    # 添加常见的大型包（可能作为依赖被引入）
    common_large = [
        'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'pillow',
        'cv2', 'opencv', 'tensorflow', 'torch', 'keras',
        'IPython', 'jupyter', 'notebook', 'ipykernel',
        'PySide6', 'PySide2', 'pygame', 'pyglet',
        'tkinter', 'Tkinter', 'openpyxl', 'xlrd', 'xlwt',
        'fastapi', 'uvicorn', 'starlette', 'pydantic',
        'flask', 'django', 'tornado', 'aiohttp',
        'sqlalchemy', 'pymysql', 'psycopg2', 'redis', 'pymongo',
        'boto3', 'botocore', 'awscli',
        'pytest', 'nose', 'coverage', 'tox', 'black', 'flake8',
    ]
    for pkg in common_large:
        if pkg.lower() not in required_lower:
            excludes.append(pkg)

    return sorted(set(excludes))

if __name__ == '__main__':
    excludes = generate_excludes()

    # 写入 build.py
    build_content = '''import PyInstaller.__main__
import os
import shutil

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Clean previous builds
for folder in ['build', 'dist']:
    if os.path.exists(folder):
        shutil.rmtree(folder)

# 自动生成的排除列表
EXCLUDE_MODULES = %s

args = [
    'main.py',
    '--onefile',
    '--windowed',
    '--name=HTML_To_MD',
    '--icon=icon.ico',
    '--add-data=icon.ico;.',
    '--hidden-import=bs4',
    '--hidden-import=lxml',
    '--hidden-import=fpdf',
    '--hidden-import=docx',
    '--hidden-import=readability',
    '--hidden-import=DrissionPage',
    '--distpath=dist',
    '--workpath=build',
]

for mod in EXCLUDE_MODULES:
    args.append(f'--exclude-module={mod}')

PyInstaller.__main__.run(args)
print("Build complete! EXE file is in the 'dist' folder.")
''' % repr(excludes)

    with open('build.py', 'w', encoding='utf-8') as f:
        f.write(build_content)

    print(f"已生成 build.py，排除了 {len(excludes)} 个模块")
    print("现在可以运行: python build.py")
