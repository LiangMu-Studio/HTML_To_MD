import PyInstaller.__main__
import os
import shutil

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Clean previous builds
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

PyInstaller.__main__.run([
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
    '--collect-all=DrissionPage',
    '--exclude-module=PySide6',
    '--exclude-module=pygame',
    '--distpath=dist',
    '--workpath=build',
])

print("Build complete! EXE file is in the 'dist' folder.")
