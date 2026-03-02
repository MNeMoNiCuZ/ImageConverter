@echo off
cd /d %~dp0
call venv\Scripts\activate

echo Generating icon...
python -c "from src.icon import generate_icon; generate_icon()"

echo Building executable...
pyinstaller --onefile --windowed --icon=src\icon.ico --name=ImageConverter --add-data="src\icon.ico;src" imageconverter.py

echo.
echo Done. Output: dist\ImageConverter.exe
pause
