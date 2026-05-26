import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm import client


def test_resolve_deepseek_config_reads_settings_json(tmp_path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "deepseek": {
                    "api_key": "settings-key",
                    "base_url": "https://settings.example/v1",
                    "model": "settings-model",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CSDATASET_HOME", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    assert client.has_configured_deepseek_api_key() is True
    assert client.resolve_deepseek_config() == (
        "settings-model",
        "settings-key",
        "https://settings.example/v1",
    )


def test_resolve_deepseek_config_prefers_env_over_dotenv(tmp_path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "DEEPSEEK_API_KEY=dotenv-key\n"
        "DEEPSEEK_BASE_URL=https://dotenv.example/v1\n"
        "DEEPSEEK_MODEL=dotenv-model\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CSDATASET_HOME", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "env-model")
    assert client.resolve_deepseek_config() == (
        "env-model",
        "env-key",
        "https://env.example/v1",
    )
