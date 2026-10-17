@echo off
rem run: gsmap-explorer with the Python of env\ (made by install.bat), from this folder.
rem python.exe is called directly, so GDAL_DATA is set here (lib-arsitektur.md section 9).
rem Arguments are passed to run.py, e.g. run.bat --mode extract
setlocal
cd /d "%~dp0"
set "PY=%~dp0env\python.exe"
if exist "%PY%" (
  set "GDAL_DATA=%~dp0env\Library\share\gdal"
) else (
  where python >nul 2>nul || goto :nopython
  set "PY=python"
  echo note: env\ not found, using the python on PATH ^(install.bat makes env\^)
)
"%PY%" run.py %*
set "CODE=%ERRORLEVEL%"
pause
exit /b %CODE%

:nopython
echo Python not found: double-click install.bat first.
pause
exit /b 1
