import PyInstaller.__main__
import os
import shutil

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Clean previous builds
for folder in ['build', 'dist']:
    if os.path.exists(folder):
        shutil.rmtree(folder)

# 自动生成的排除列表
EXCLUDE_MODULES = ['IPython', 'PIL', 'PySide2', 'PySide6', 'Tkinter', 'absl-py', 'accelerate', 'aiofiles', 'aiohappyeyeballs', 'aiohttp', 'aiosignal', 'altair', 'annotated-types', 'anthropic', 'antlr4-python3-runtime', 'anyio', 'arabic-reshaper', 'argon2-cffi', 'argon2-cffi-bindings', 'arrow', 'asn1crypto', 'astroid', 'asttokens', 'astunparse', 'async-timeout', 'attrs', 'audioread', 'awscli', 'azure-cognitiveservices-speech', 'azure-core', 'babel', 'backcall', 'bidict', 'black', 'bleach', 'borax', 'boto3', 'botocore', 'brotli', 'browser-cookie3', 'cachetools', 'cffi', 'chardet', 'click', 'colorama', 'comm', 'contourpy', 'controlnet-aux', 'courlan', 'coverage', 'cryptography', 'cssselect2', 'customtkinter', 'cv2', 'cycler', 'cython', 'darkdetect', 'datarecorder', 'dateparser', 'debugpy', 'decorator', 'defusedxml', 'diffusers', 'dill', 'distro', 'django', 'docstring_parser', 'downloadkit', 'easydict', 'einops', 'et_xmlfile', 'exceptiongroup', 'executing', 'fastapi', 'fastjsonschema', 'ffmpeg-python', 'ffmpy', 'fire', 'flake8', 'flask', 'flatbuffers', 'flet', 'flet-desktop', 'fonttools', 'fqdn', 'freetype-py', 'frida', 'frida-tools', 'frozenlist', 'fsspec', 'future', 'gast', 'google-auth', 'google-auth-oauthlib', 'google-pasta', 'gradio', 'gradio_client', 'greenlet', 'grpcio', 'h11', 'h2', 'h5py', 'hpack', 'html5lib', 'htmldate', 'httpcore', 'httpx', 'huggingface-hub', 'hyperframe', 'imageio', 'importlib_metadata', 'importlib_resources', 'iopaint', 'iopath', 'ipykernel', 'ipython', 'ipython-genutils', 'ipywidgets', 'isoduration', 'isort', 'jax', 'jedi', 'jieba', 'jinja2', 'jiter', 'joblib', 'jsonpointer', 'jsonschema', 'jupyter', 'jupyter-console', 'jupyter-events', 'jupyter_client', 'jupyter_core', 'jupyter_server', 'jupyter_server_terminals', 'jupyterlab-pygments', 'jupyterlab-widgets', 'justext', 'keras', 'kiwisolver', 'lazy_loader', 'libclang', 'librosa', 'llvmlite', 'loguru', 'lxml_html_clean', 'lz4', 'markdown-it-py', 'markupsafe', 'matplotlib', 'matplotlib-inline', 'mccabe', 'mdurl', 'metatrader5', 'mistune', 'ml-dtypes', 'mpmath', 'msgpack', 'multidict', 'mypy', 'mypy-extensions', 'narwhals', 'nbclassic', 'nbclient', 'nbconvert', 'nbformat', 'nest-asyncio', 'networkx', 'nose', 'notebook', 'notebook_shim', 'numba', 'numpy', 'oauthlib', 'omegaconf', 'opencc-python-reimplemented', 'opencv', 'opencv-python', 'opt-einsum', 'orjson', 'oscrypto', 'outcome', 'packaging', 'pandas', 'pandocfilters', 'parso', 'pathspec', 'pdf2image', 'peft', 'pickleshare', 'piexif', 'pillow', 'pip', 'platformdirs', 'pooch', 'portalocker', 'prettytable', 'prometheus-client', 'prompt-toolkit', 'propcache', 'protobuf', 'psutil', 'psycopg2', 'pure-eval', 'pyasn1', 'pyasn1-modules', 'pyaudio', 'pycairo', 'pycodestyle', 'pycparser', 'pycryptodome', 'pycryptodomex', 'pydantic', 'pydantic_core', 'pydub', 'pydyf', 'pyecharts', 'pyee', 'pyflakes', 'pygame', 'pyglet', 'pyglossary', 'pygments', 'pyhanko', 'pyhanko-certvalidator', 'pylint', 'pymongo', 'pymysql', 'pyparsing', 'pypdf', 'pyphen', 'pyqt5-plugins', 'pyqt5-qt5', 'pyqt5-tools', 'pyqt5_sip', 'pyqt5designer', 'pyrsistent', 'pyrubberband', 'pyside6', 'pyside6_addons', 'pyside6_essentials', 'pysocks', 'pytest', 'python-bidi', 'python-dateutil', 'python-dotenv', 'python-engineio', 'python-json-logger', 'python-lzo', 'python-multipart', 'python-socketio', 'pytz', 'pywinpty', 'pyyaml', 'pyzmq', 'qt5-applications', 'qt5-tools', 'qtconsole', 'qtpy', 'redis', 'regex', 'repath', 'reportlab', 'requests-oauthlib', 'rfc3339-validator', 'rfc3986-validator', 'rich', 'rlpycairo', 'rsa', 'ruff', 'safetensors', 'scikit-image', 'scikit-learn', 'scipy', 'semantic-version', 'send2trash', 'setuptools', 'shadowcopy', 'shellingham', 'shiboken6', 'simple-websocket', 'simplejson', 'six', 'sniffio', 'sortedcontainers', 'soundfile', 'soxr', 'sqlalchemy', 'stack-data', 'starlette', 'svglib', 'sympy', 'tensorboard', 'tensorboard-data-server', 'tensorflow', 'tensorflow-estimator', 'tensorflow-intel', 'tensorflow-io-gcs-filesystem', 'termcolor', 'terminado', 'threadpoolctl', 'tifffile', 'timm', 'tinycss2', 'tinyhtml5', 'tkinter', 'tld', 'tokenizers', 'tomli', 'tomlkit', 'torch', 'torchvision', 'tornado', 'tox', 'tqdm', 'trafilatura', 'traitlets', 'transformers', 'trio', 'trio-websocket', 'typer', 'typer-config', 'typing-inspection', 'typing_extensions', 'tzdata', 'tzlocal', 'uri-template', 'uritools', 'uvicorn', 'wcwidth', 'webcolors', 'webencodings', 'websockets', 'werkzeug', 'wheel', 'widgetsnbextension', 'win32_setctime', 'win_inet_pton', 'wmi', 'wrapt', 'wsproto', 'xlrd', 'xlwt', 'yacs', 'yapf', 'yarl', 'zhdate', 'zipp', 'zopfli', 'zstandard']

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
