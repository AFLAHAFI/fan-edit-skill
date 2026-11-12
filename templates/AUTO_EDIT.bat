@echo off
rem ===== mass-fan-edit : ONE-CLICK auto edit (no Claude needed) =====
rem Folder layout:  raw\ = your clips    song\ = one song
rem Edit the 4 settings below, save, double-click.
set SKILL_DIR=C:\mass-fan-edit
set PRESET=mass-hero
rem   mass-hero  phonk-night  cinematic-trailer  emotional  anime-hype  villain-glitch  retro-synthwave
set ASPECT=16:9
rem   16:9  9:16  1:1  4:5
set WORDS=
rem   e.g.  set WORDS=the/AMAZING,SPIDER-MAN,spidey/SENSE,POWER     (empty = song title)
set DUR=38
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo FFmpeg not found on PATH. Get it from https://www.gyan.dev/ffmpeg/builds/ & pause & exit /b 1)
where python >nul 2>nul || (echo Python not found. Install Python 3.10+ and tick "Add to PATH". & pause & exit /b 1)
python -m pip install --quiet -r "%SKILL_DIR%\templates\requirements.txt"
for %%f in (song\*.mp3 song\*.wav song\*.m4a) do set SONG=%%f
if "%SONG%"=="" (echo No song in song\ & pause & exit /b 1)
echo [1/3] Analyzing song ...
python "%SKILL_DIR%\scripts\analyze_song.py" "%SONG%" --dur %DUR% || (pause & exit /b 1)
echo [2/3] Building project.json ...
python "%SKILL_DIR%\scripts\auto_project.py" "%~dp0." --preset %PRESET% --aspect %ASPECT% --words "%WORDS%" || (pause & exit /b 1)
echo [3/3] Auto-picking shots + rendering (first run scans the videos, can take 10-20 min) ...
if exist picks.json ren picks.json picks.json.bak
python "%SKILL_DIR%\scripts\massedit.py" --project "%~dp0." || (echo RENDER FAILED & pause & exit /b 1)
echo Done. Video is in this folder.
pause
