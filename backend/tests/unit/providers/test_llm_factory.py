from src.providers import factory
from src.providers.openai_compatible_llm_provider import OpenAiCompatibleLlmProvider


def test_none_when_base_url_empty(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_base_url", "")
    monkeypatch.setattr(factory.settings, "llm_model", "test-model")

    assert factory.get_llm_provider() is None


def test_none_when_model_empty(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(factory.settings, "llm_model", "")

    assert factory.get_llm_provider() is None


def test_returns_provider_when_configured(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(factory.settings, "llm_model", "test-model")

    assert isinstance(factory.get_llm_provider(), OpenAiCompatibleLlmProvider)


def test_returns_new_provider_each_call(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(factory.settings, "llm_model", "test-model")

    assert factory.get_llm_provider() is not factory.get_llm_provider()


def test_ai_insights_disabled_does_not_return_none(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(factory.settings, "llm_model", "test-model")
    monkeypatch.setattr(factory.settings, "ai_insights_enabled", False)

    assert factory.get_llm_provider() is not None
