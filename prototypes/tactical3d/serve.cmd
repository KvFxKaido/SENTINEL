@echo off
REM Serve the 3D tactical prototype. ES modules are blocked over file://,
REM so the folder has to come off a real (local) HTTP server.
REM
REM The server root is the repo: index.html imports shared rules from
REM prototypes/ and molded fighter sheets from assets/.
setlocal
set PORT=8080
set ROOT=%~dp0..\..

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" http://localhost:%PORT%/prototypes/tactical3d/
  python -m http.server %PORT% -d "%ROOT%"
  goto :eof
)

where node >nul 2>nul
if %ERRORLEVEL%==0 (
  start "" http://localhost:%PORT%/prototypes/tactical3d/
  npx --yes http-server "%ROOT%" -p %PORT% -c-1
  goto :eof
)

echo Neither python nor node found on PATH.
echo Serve the repo root with any static file server,
echo then open http://localhost:8080/prototypes/tactical3d/
pause
