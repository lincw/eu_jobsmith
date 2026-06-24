import importlib

import app.settings as settings_mod
import app.llm as llm_mod


def _reload(monkeypatch, backend):
    monkeypatch.setenv("LLM_BACKEND", backend)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    importlib.reload(settings_mod)
    importlib.reload(llm_mod)
    return llm_mod


def test_anthropic_backend_selected(monkeypatch):
    m = _reload(monkeypatch, "anthropic")
    llm = m.get_llm("standard")
    assert llm.model == "claude-sonnet-4-6"


def test_unknown_backend_raises(monkeypatch):
    m = _reload(monkeypatch, "nonsense")
    import pytest
    with pytest.raises(ValueError):
        m.get_llm("standard")


def test_set_backend_switches_at_runtime(monkeypatch):
    _reload(monkeypatch, "claude_cli")
    assert settings_mod.current_backend() == "claude_cli"
    settings_mod.set_backend("codex_cli")
    assert settings_mod.current_backend() == "codex_cli"
    from app.llm_cli import CodexCLIChat
    assert isinstance(llm_mod.get_llm("standard"), CodexCLIChat)


def test_set_backend_rejects_unsupported(monkeypatch):
    import pytest
    _reload(monkeypatch, "claude_cli")
    with pytest.raises(ValueError):
        settings_mod.set_backend("qianfan")


def test_claude_cli_backend_selected(monkeypatch):
    m = _reload(monkeypatch, "claude_cli")
    from app.llm_cli import ClaudeCLIChat
    llm = m.get_llm("deep")
    assert isinstance(llm, ClaudeCLIChat)
    assert llm.model == "opus"


def test_codex_cli_backend_selected(monkeypatch):
    m = _reload(monkeypatch, "codex_cli")
    from app.llm_cli import CodexCLIChat
    llm = m.get_llm("standard")
    assert isinstance(llm, CodexCLIChat)
