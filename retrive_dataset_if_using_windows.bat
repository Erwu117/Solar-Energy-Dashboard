@echo off
:: Ensure curl is available
where curl >nul 2>nul
if errorlevel 1 (
    echo curl is not installed. Please install it to proceed.
    exit /b
)

:: Ensure the datasets folder exists
if not exist datasets (
    mkdir datasets
)

:: Set the Dropbox file URL and file name
set DROPBOX_FILE_URL=https://dl.dropboxusercontent.com/scl/fi/2fl5d5fryskuhvhbr76q2/solar_data.geojson?rlkey=1j1673ne3nf4ql83lud2t8h7g&st=797t1mzh&dl=0
set FILE_NAME=solar_data.geojson

:: Fetch the file using curl
curl -L -o "%FILE_NAME%" "%DROPBOX_FILE_URL%"

:: Move the file to the datasets folder
move "%FILE_NAME%" datasets\

echo File downloaded and moved to the datasets folder.