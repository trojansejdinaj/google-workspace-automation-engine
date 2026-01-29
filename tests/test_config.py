from pathlib import Path

import pytest

from gw_engine.config import ConfigError, load_config


def test_default_profile_local(tmp_path: Path) -> None:
    # .env.example must exist for local/dev; create it.
    (tmp_path / ".env.example").write_text("GW_PROFILE=local\n", encoding="utf-8")
    cfg = load_config(env={}, base_dir=tmp_path)
    assert cfg.profile == "local"
    assert cfg.runs_dir.name == "runs"


def test_profile_invalid_rejected(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("GW_PROFILE=local\n", encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        load_config(env={"GW_PROFILE": "nope"}, base_dir=tmp_path)
    assert "Invalid GW_PROFILE" in str(e.value)


def test_prod_requires_auth(tmp_path: Path) -> None:
    # prod doesn't require .env.example, but requires auth
    with pytest.raises(ConfigError) as e:
        load_config(env={"GW_PROFILE": "prod"}, base_dir=tmp_path)
    assert "Prod auth is not configured" in str(e.value)


def test_dotenv_profile_overrides(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("GW_PROFILE=local\n", encoding="utf-8")
    (tmp_path / ".env").write_text("GW_PROFILE=local\nGW_LOG_LEVEL=DEBUG\n", encoding="utf-8")
    (tmp_path / ".env.dev").write_text("GW_LOG_LEVEL=INFO\n", encoding="utf-8")

    cfg = load_config(env={"GW_PROFILE": "dev"}, base_dir=tmp_path)
    assert cfg.profile == "dev"
    assert cfg.log_level == "INFO"
