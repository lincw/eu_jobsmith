"""依 LLM_BACKEND 建立 LLM（介面一致：.with_structured_output(...).invoke(...)）。

支援後端：
- claude_cli / codex_cli：本機 CLI 訂閱（免 API key、不吃額度）——使用者可在 UI 切換（主要）。
- anthropic：API key（雲端/部署用，可選）。
"""
from app import settings
from app.settings import get_model


def get_llm(tier: str, *, temperature: float = 0, max_tokens: int = 2000):
    """依分層與『當前後端』回傳設定好的 chat model（含重試）。"""
    backend = settings.current_backend()
    if backend == "claude_cli":
        from app.llm_cli import ClaudeCLIChat, CLAUDE_TIER_MODELS
        return ClaudeCLIChat(CLAUDE_TIER_MODELS[tier], max_tokens=max_tokens)
    if backend == "codex_cli":
        from app.llm_cli import CodexCLIChat
        return CodexCLIChat(tier, max_tokens=max_tokens)
    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=get_model(tier),
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=4,
        )
    raise ValueError(f"unknown LLM_BACKEND: {backend!r}")


def research_structured(schema, messages, tier: str = "standard"):
    """若當前後端有內建上網工具（目前為 claude_cli 的 WebSearch/WebFetch），用之做結構化
    研究並回傳驗證後的模型；後端不支援則回 None，由呼叫端自行降級（如 Tavily / 一般知識）。"""
    backend = settings.current_backend()
    if backend == "claude_cli":
        from app.llm_cli import run_claude_structured_research, CLAUDE_TIER_MODELS
        return run_claude_structured_research(schema, messages, CLAUDE_TIER_MODELS[tier])
    return None
