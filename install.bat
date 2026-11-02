@echo off
rem install: creates the Python env of gsmap-explorer in env\ from environment.yml.
rem Pattern of kerja-di-luar-dev.md section 3 (owner 2026-09-30): a conda -p env inside the
rem folder, packages from conda-forge (internet needed). Run again after the folder was moved
rem (a conda -p env cannot be moved). Needs Miniforge.
rem Test mode: install.bat /check  (only reports what it would do).
setlocal
set "ROOT=%~dp0"
set "ENV=%ROOT%env"
rem conda: CONDA_EXE (set in a Miniforge Prompt), then the Miniforge folders of the installer
rem ("Just Me" and "All Users"), then conda on PATH.
set "CONDA=%CONDA_EXE%"
if defined CONDA if not exist "%CONDA%" set "CONDA="
for %%D in ("%USERPROFILE%\miniforge3" "%LOCALAPPDATA%\miniforge3" "%ProgramData%\miniforge3") do (
  if not defined CONDA if exist "%%~D\Scripts\conda.exe" set "CONDA=%%~D\Scripts\conda.exe"
)
if not defined CONDA for /f "delims=" %%C in ('where conda.exe 2^>nul') do if not defined CONDA set "CONDA=%%C"
if not defined CONDA (
  echo conda not found in "%USERPROFILE%\miniforge3", "%LOCALAPPDATA%\miniforge3", "%ProgramData%\miniforge3" or PATH.
  echo Install Miniforge first ^(https://github.com/conda-forge/miniforge^), or run install.bat from a Miniforge Prompt.
  goto :fail
)
echo conda : "%CONDA%"
echo env   : "%ENV%"
if /i "%~1"=="/check" (
  if exist "%ENV%\python.exe" (echo check only: would update the env from environment.yml) else (echo check only: would run conda env create -p "%ENV%" -f "%ROOT%environment.yml")
  echo check only: then run.py --download-maps ^(Natural Earth map layers^)
  exit /b 0
)
if exist "%ENV%\python.exe" (
  echo env exists: updating it from environment.yml
  "%CONDA%" env update -p "%ENV%" -f "%ROOT%environment.yml" --prune || goto :fail
) else (
  "%CONDA%" env create -p "%ENV%" -f "%ROOT%environment.yml" || goto :fail
)
rem pyexpat first: rasterio's GDAL breaks the expat DLL when loaded before it (Windows, 2026-10-17)
"%ENV%\python.exe" -c "import pyexpat, netCDF4, geopandas, cartopy, rasterio, shapely, pyproj, matplotlib, pandas, numpy; print('libraries: ok')" || goto :fail
rem The Natural Earth layers of the maps, now instead of at the first map. Offline: a note only,
rem the maps download them later.
"%ENV%\python.exe" "%ROOT%run.py" --download-maps || echo note: map layers not downloaded now; the first map downloads them ^(internet needed^).
echo.
echo Installed. Next: copy config\input.local.example.txt to config\input.local.txt,
echo fill in gsmap_folder, then double-click run.bat.
echo Petunjuk lengkap: docs\manual.pdf
pause
exit /b 0

:fail
echo.
echo Install failed: see the messages above.
pause
exit /b 1
