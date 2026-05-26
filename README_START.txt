Construction Safety Assistant

How to start
1. Run `ConstructionSafetyAssistant-Installer.exe`.
2. After installation, double-click `Construction Safety Assistant` on the Desktop or from the Start Menu.
3. The app opens in your browser at `http://127.0.0.1:8501`.

Notes
- The packaged app already contains its Python runtime and dependencies.
- App data is stored under `%LOCALAPPDATA%\ConstructionSafetyAssistant\Data`.
- DeepSeek config can be provided via `DEEPSEEK_*` environment variables, `%LOCALAPPDATA%\ConstructionSafetyAssistant\Data\settings.json`, or `%LOCALAPPDATA%\ConstructionSafetyAssistant\Data\.env`.
- If you want the installer to ship with a built-in DeepSeek config, either place `settings.json` or `.env` in the project root before packaging, or set `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` in your build environment. The launcher will seed the bundled config into `%LOCALAPPDATA%\ConstructionSafetyAssistant\Data` on first run.
- If the browser does not open automatically, visit `http://127.0.0.1:8501` manually.
- Closing the browser tab does not stop the local app service. Run `stop_app.bat` from the project folder if you want to fully exit it.
- If startup fails, check `%LOCALAPPDATA%\ConstructionSafetyAssistant\launcher.log`.
