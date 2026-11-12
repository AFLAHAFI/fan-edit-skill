@echo off
rem ===== mass-fan-edit : step 1 (analyze song + footage) =====
rem Put this file in your project folder (with raw\ and song\ inside). Set SKILL_DIR to where you cloned the repo.
set SKILL_DIR=C:\mass-fan-edit
set DUR=38
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo FFmpeg not found on PATH. Get it from https://www.gyan.dev/ffmpeg/builds/ & pause & exit /b 1)
where python >nul 2>nul || (echo Python not found. Install Python 3.10+ and tick "Add to PATH". & pause & exit /b 1)
python -m pip install --quiet -r "%SKILL_DIR%\templates\requirements.txt"
for %%f in (song\*.mp3 song\*.wav song\*.m4a) do set SONG=%%f
if "%SONG%"=="" (echo No song in song\ & pause & exit /b 1)
python "%SKILL_DIR%\scripts\analyze_song.py" "%SONG%" --dur %DUR% %1 %2
python "%SKILL_DIR%\scripts\make_sheets.py" "%~dp0." --proxy
echo.
echo Upload to Claude: song_report.txt, video_report.txt and the images in sheets\
pause
