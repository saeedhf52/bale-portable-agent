@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"

echo Packaging bale-portable-agent.zip...

if exist "%~dp0runtime\python.exe" (
    set "PYEXE=%~dp0runtime\python.exe"
) else (
    set "PYEXE=python"
)

"%PYEXE%" -c "import zipfile, os, sys, pathlib; root = pathlib.Path(sys.argv[1]); zip_path = root / 'bale-portable-agent.zip'; exclude_dirs = {'.git', 'output', 'BrowserProfile', '__pycache__', '.vscode', '.idea'}; exclude_files = {'bale-portable-agent.zip', '.gitignore'}; z = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED); [z.write(p, p.relative_to(root)) for p in root.rglob('*') if p != zip_path and not any(part in exclude_dirs for part in p.parts) and p.name not in exclude_files and p.is_file()]; z.close(); print(f'ZIP created: {zip_path}')" "%~dp0."

if %errorlevel% equ 0 (
    echo Package completed successfully.
) else (
    echo Packaging failed.
)
pause
