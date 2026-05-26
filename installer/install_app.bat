@echo off
setlocal

set "APP_NAME=Construction Safety Assistant"
set "INSTALL_BASE=%LOCALAPPDATA%\ConstructionSafetyAssistant"
set "INSTALL_DIR=%INSTALL_BASE%\App"
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Construction Safety Assistant"
set "DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\%APP_NAME%.lnk"
set "START_MENU_SHORTCUT=%START_MENU_DIR%\%APP_NAME%.lnk"
set "TARGET_EXE=%INSTALL_DIR%\ConstructionSafetyAssistant.exe"

if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
if exist "%START_MENU_DIR%" rmdir /s /q "%START_MENU_DIR%"

mkdir "%INSTALL_BASE%" >nul 2>nul
mkdir "%START_MENU_DIR%" >nul 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%~dp0ConstructionSafetyAssistant.zip' -DestinationPath '%INSTALL_BASE%' -Force"
if errorlevel 1 (
  echo [ERROR] Failed to extract application files.
  pause
  exit /b 1
)

if not exist "%TARGET_EXE%" (
  echo [ERROR] Installation finished, but the launcher was not found.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $desktop=$shell.CreateShortcut('%DESKTOP_SHORTCUT%'); $desktop.TargetPath='%TARGET_EXE%'; $desktop.WorkingDirectory='%INSTALL_DIR%'; $desktop.IconLocation='%TARGET_EXE%,0'; $desktop.Save(); $menu=$shell.CreateShortcut('%START_MENU_SHORTCUT%'); $menu.TargetPath='%TARGET_EXE%'; $menu.WorkingDirectory='%INSTALL_DIR%'; $menu.IconLocation='%TARGET_EXE%,0'; $menu.Save()"
if errorlevel 1 (
  echo [ERROR] Failed to create shortcuts.
  pause
  exit /b 1
)

start "" "%TARGET_EXE%"
exit /b 0
