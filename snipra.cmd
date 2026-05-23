@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "COMMAND=%~1"

if "%COMMAND%"=="" goto help
shift

if /I "%COMMAND%"=="dev" (
  npm.cmd --prefix "%PROJECT_DIR%" run dev -- %2 %3 %4 %5 %6 %7 %8 %9
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="build" (
  npm.cmd --prefix "%PROJECT_DIR%" run build
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="type-check" (
  npm.cmd --prefix "%PROJECT_DIR%" run type-check
  exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="start" (
  npm.cmd --prefix "%PROJECT_DIR%" run start -- %2 %3 %4 %5 %6 %7 %8 %9
  exit /b %ERRORLEVEL%
)

:help
echo Usage: snipra.cmd ^<dev^|build^|type-check^|start^> [args]
echo Example: snipra.cmd dev --port 3000
exit /b 1
