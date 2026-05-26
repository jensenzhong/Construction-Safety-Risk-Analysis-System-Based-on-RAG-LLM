from pathlib import Path

import launcher


def test_prepare_runtime_tree_copies_optional_config_files(tmp_path) -> None:
    bundle_root = tmp_path / "bundle"
    app_home = tmp_path / "appdata"
    bundle_root.mkdir()

    settings_text = '{"deepseek":{"api_key":"seed-key","base_url":"https://seed.example/v1","model":"seed-model"}}'
    dotenv_text = "DEEPSEEK_API_KEY=seed-key\nDEEPSEEK_BASE_URL=https://seed.example/v1\nDEEPSEEK_MODEL=seed-model\n"

    (bundle_root / "settings.json").write_text(settings_text, encoding="utf-8")
    (bundle_root / ".env").write_text(dotenv_text, encoding="utf-8")

    launcher._prepare_runtime_tree(bundle_root, app_home)

    assert (app_home / "settings.json").read_text(encoding="utf-8") == settings_text
    assert (app_home / ".env").read_text(encoding="utf-8") == dotenv_text


def test_prepare_runtime_tree_does_not_overwrite_existing_config(tmp_path) -> None:
    bundle_root = tmp_path / "bundle"
    app_home = tmp_path / "appdata"
    bundle_root.mkdir()
    app_home.mkdir(parents=True)

    (bundle_root / "settings.json").write_text('{"deepseek":{"api_key":"bundle-key"}}', encoding="utf-8")
    (app_home / "settings.json").write_text('{"deepseek":{"api_key":"existing-key"}}', encoding="utf-8")

    launcher._prepare_runtime_tree(bundle_root, app_home)

    assert (app_home / "settings.json").read_text(encoding="utf-8") == '{"deepseek":{"api_key":"existing-key"}}'
