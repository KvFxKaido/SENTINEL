@echo off
REM Serve the 3D tactical prototype. ES modules are blocked over file://,
REM so the folder has to come off a real (local) HTTP server.
REM
REM The server root is prototypes/, not this folder: index.html imports the
REM shared rules from ../tactical-core/rules.js, which has to be reachable.
setlocal
set PORT=8080
set ROOT=%~dp0..

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" http://localhost:%PORT%/tactical3d/
  python -m http.server %PORT% -d "%ROOT%"
  goto :eof
)

where node >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" http://localhost:%PORT%/tactical3d/
  npx --yes http-server "%ROOT%" -p %PORT% -c-1
  goto :eof
)

echo Neither python nor node found on PATH.
echo Serve the prototypes/ folder with any static file server,
echo then open http://localhost:8080/tactical3d/
pause
