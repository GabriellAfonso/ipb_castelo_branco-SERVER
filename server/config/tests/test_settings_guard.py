"""Guard against production booting with a non-production settings module."""

import pytest

from config.settings.base import reject_dev_settings_in_production


@pytest.mark.parametrize("value", ["prod", "production", "PROD", "  Production  "])
def test_raises_when_django_env_asks_for_production(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("DJANGO_ENV", value)

    with pytest.raises(RuntimeError, match="config.settings.prod"):
        reject_dev_settings_in_production("config.settings.dev")


def test_message_names_the_module_that_was_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_ENV", "prod")

    with pytest.raises(RuntimeError, match="config.settings.dev was loaded"):
        reject_dev_settings_in_production("config.settings.dev")


@pytest.mark.parametrize("value", ["dev", "", "staging"])
def test_allows_every_non_production_env(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("DJANGO_ENV", value)

    reject_dev_settings_in_production("config.settings.dev")


def test_allows_unset_django_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DJANGO_ENV", raising=False)

    reject_dev_settings_in_production("config.settings.dev")
