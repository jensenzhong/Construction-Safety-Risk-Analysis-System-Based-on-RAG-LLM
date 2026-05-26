import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_API_KEY = ""


def _clean_config_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _candidate_config_dirs() -> list[Path]:
    candidates = []
    raw_candidates = [
        os.getenv("CSDATASET_HOME"),
        Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None,
        Path.cwd(),
        Path(__file__).resolve().parents[1],
    ]
    for raw_candidate in raw_candidates:
        if not raw_candidate:
            continue
        candidate = Path(raw_candidate).resolve()
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _normalize_config_mapping(raw_mapping) -> dict[str, str]:
    normalized = {}
    if not isinstance(raw_mapping, dict):
        return normalized

    top_level_aliases = {
        "DEEPSEEK_API_KEY": ("DEEPSEEK_API_KEY", "deepseek_api_key"),
        "DEEPSEEK_BASE_URL": ("DEEPSEEK_BASE_URL", "deepseek_base_url"),
        "DEEPSEEK_MODEL": ("DEEPSEEK_MODEL", "deepseek_model"),
    }
    for target_key, aliases in top_level_aliases.items():
        for alias in aliases:
            value = _clean_config_value(raw_mapping.get(alias))
            if value:
                normalized[target_key] = value
                break

    nested_mapping = raw_mapping.get("deepseek")
    if isinstance(nested_mapping, dict):
        nested_aliases = {
            "DEEPSEEK_API_KEY": "api_key",
            "DEEPSEEK_BASE_URL": "base_url",
            "DEEPSEEK_MODEL": "model",
        }
        for target_key, alias in nested_aliases.items():
            if target_key in normalized:
                continue
            value = _clean_config_value(nested_mapping.get(alias))
            if value:
                normalized[target_key] = value

    return normalized


def _load_settings_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return _normalize_config_mapping(payload)


def _strip_inline_comment(value: str) -> str:
    if not value or value[0] in "\"'":
        return value
    comment_pos = value.find("#")
    if comment_pos >= 0:
        return value[:comment_pos].rstrip()
    return value


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return values

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = _strip_inline_comment(value.strip())
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value

    return _normalize_config_mapping(values)


def _load_file_config() -> dict[str, str]:
    merged = {}
    for config_dir in _candidate_config_dirs():
        for config_path, loader in (
            (config_dir / "settings.json", _load_settings_json),
            (config_dir / ".env", _load_dotenv),
        ):
            loaded = loader(config_path)
            for key, value in loaded.items():
                if value and key not in merged:
                    merged[key] = value
    return merged


def _resolve_config_value(explicit_value, env_name: str, default_value: str = "") -> str:
    for candidate in (
        _clean_config_value(explicit_value),
        _clean_config_value(os.getenv(env_name)),
        _clean_config_value(_load_file_config().get(env_name)),
        _clean_config_value(default_value),
    ):
        if candidate:
            return candidate
    return ""


def has_configured_deepseek_api_key() -> bool:
    return bool(_resolve_config_value(None, "DEEPSEEK_API_KEY", DEFAULT_DEEPSEEK_API_KEY))


def resolve_deepseek_config(
    model: str = None,
    api_key: str = None,
    base_url: str = None,
):
    resolved_api_key = _resolve_config_value(api_key, "DEEPSEEK_API_KEY", DEFAULT_DEEPSEEK_API_KEY)
    resolved_base_url = _resolve_config_value(base_url, "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)
    resolved_model = _resolve_config_value(model, "DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)

    if not resolved_api_key:
        raise RuntimeError(
            "Missing DeepSeek API key. Please set DEEPSEEK_API_KEY, or provide it via .env or settings.json."
        )

    return resolved_model, resolved_api_key, resolved_base_url


def chat(
    prompt: str,
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    temperature: float = 0.0,
    max_tokens: int = None,
    timeout: float = 20.0,
) -> str:
    resolved_model, resolved_api_key, resolved_base_url = resolve_deepseek_config(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )

    kwargs = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if OpenAI is not None:
        client = OpenAI(api_key=resolved_api_key, base_url=resolved_base_url, timeout=timeout)
        resp = client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()

    return _chat_via_http(
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        payload=kwargs,
        timeout=timeout,
    )


def _chat_via_http(base_url: str, api_key: str, payload: dict, timeout: float) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = str(exc)
        raise RuntimeError(f"DeepSeek HTTP error {exc.code}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek HTTP request failed: {exc}") from exc

    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        raise RuntimeError(f"Unexpected DeepSeek response format: {data}") from exc
