@echo off
rem Join a friend's world: starts only the game client, never the local server or save.
rem A game folder carries its own .NET runtime in ..\tools\dotnet, as START OFFLINE DAOC.cmd uses.
if exist "%~dp0..\tools\dotnet\dotnet.exe" (
  set "DOTNET_ROOT=%~dp0..\tools\dotnet"
  set "DOTNET_ROOT_X64=%~dp0..\tools\dotnet"
  set "DOTNET_MULTILEVEL_LOOKUP=0"
)
start "" "%~dp0OfflineDAoC.exe" --join
