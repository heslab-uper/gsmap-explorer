@echo off

echo ==========================
echo   PILIH MODE PROGRAM
echo ==========================
echo 1. Extract CSV
echo 2. Visualisasi
echo 3. Hujan Regional (Thiessen)
echo 4. Analisis Hujan (kala ulang, IDF, karakteristik jam-jaman)
echo 5. Hujan di Titik Koordinat (jam-an dan harian)
echo 6. Semua
echo.

set /p choice=Pilih opsi (1/2/3/4/5/6):

if "%choice%"=="1" python run.py --mode extract
if "%choice%"=="2" python run.py --mode visualize
if "%choice%"=="3" python run.py --mode thiessen
if "%choice%"=="4" python run.py --mode analysis
if "%choice%"=="5" python run.py --mode points
if "%choice%"=="6" python run.py --mode all

pause