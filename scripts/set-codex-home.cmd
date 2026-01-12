@echo off
set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
set "CODEX_HOME=%REPO_ROOT%\.codex"
echo CODEX_HOME set to %CODEX_HOME% for this session.
echo Run Codex from this shell to use project-local skills.
