@echo off
python -m venv myenv
call myenv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo Tests failed. Aborting.
    exit /b 1
)

echo.
echo All tests passed. Starting app...
python backup_gui.py
