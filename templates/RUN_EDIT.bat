@echo off
rem ===== mass-fan-edit : render =====
rem   RUN_EDIT.bat          preview + final 1080p
rem   RUN_EDIT.bat plan     only write _work\slots.txt (cut list for picking shots)
rem   RUN_EDIT.bat final    final only
set SKILL_DIR=C:\mass-fan-edit
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo FFmpeg not found on PATH. & pause & exit /b 1)
python -m pip install --quiet numpy opencv-python pillow
if /i "%1"=="plan" (python "%SKILL_DIR%\scripts\massedit.py" --project "%~dp0." --dump-plan & type _work\slots.txt & pause & exit /b 0)
if /i "%1"=="verify" (python "%SKILL_DIR%\scripts\verify_picks.py" "%~dp0." & pause & exit /b 0)
if /i not "%1"=="final" (
  python "%SKILL_DIR%\scripts\massedit.py" --project "%~dp0." --preview || (echo PREVIEW FAILED & pause & exit /b 1)
)
python "%SKILL_DIR%\scripts\massedit.py" --project "%~dp0." || (echo RENDER FAILED & pause & exit /b 1)
echo Done.
pause
