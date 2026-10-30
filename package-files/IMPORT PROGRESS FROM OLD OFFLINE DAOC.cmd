@echo off
setlocal
cd /d "%~dp0"
rem Moves characters, account, items, money, houses and bots from an OLDER Offline DAoC
rem folder into THIS one. The old folder is only read. A rollback backup is made first.
if not exist "%~dp0tools\ProgressImporter\OfflineDaoc.ProgressImport.exe" (
  echo The progress importer is missing from this folder. Extract the whole download again.
  pause
  exit /b 1
)
set "DOTNET_ROOT=%~dp0tools\dotnet"
set "DOTNET_ROOT_X64=%~dp0tools\dotnet"
set "DOTNET_MULTILEVEL_LOOKUP=0"
start "" "%~dp0tools\ProgressImporter\OfflineDaoc.ProgressImport.exe"
