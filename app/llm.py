"""依 LLM_BACKEND 建立 LLM（介面一致：.with_structured_output(...).invoke(...)）。

支援後端：
- claude_cli / codex_cli：本機 CLI 訂閱（免 API key、不吃額度）——使用者可在 UI 切換（主要）。
- anthropic：API key（雲端/部署用，可選）。
"""
from app import settings
from app.llm_errors import ensure_structured_result, normalize_structured_exception
from app.settings import get_model

import contextvars
current_lang = contextvars.ContextVar('current_lang', default='zh')

class LangWrapper:
    def __init__(self, inner):
        self._inner = inner
        
    def with_structured_output(self, schema):
        return LangWrapper(self._inner.with_structured_output(schema))
        
    def invoke(self, messages, *args, **kwargs):
        lang = current_lang.get()
        prompt_addition = ""
        if lang == 'en':
            prompt_addition = "\\n\\nCRITICAL: The user has set their language preference to English. YOU MUST RESPOND ENTIRELY IN ENGLISH."
        else:
            prompt_addition = "\\n\\nCRITICAL: The user has set their language preference to Traditional Chinese (zh-TW). YOU MUST RESPOND ENTIRELY IN TRADITIONAL CHINESE (Taiwan Style), including all special terms, labels, explanations, and outputs. NO SIMPLIFIED CHINESE."

        new_msgs = list(messages)
        for i, m in enumerate(new_msgs):
            if isinstance(m, tuple) and m[0] == 'system':
                new_msgs[i] = ('system', m[1] + prompt_addition)
                break
            elif hasattr(m, 'type') and m.type == 'system':
                import copy
                new_m = copy.copy(m)
                new_m.content += prompt_addition
                new_msgs[i] = new_m
                break
        messages = new_msgs
        return self._inner.invoke(messages, *args, **kwargs)
        
    def __getattr__(self, name):
        return getattr(self._inner, name)




class _FriendlyStructured:
    def __init__(self, inner, schema, backend_label: str):
        self._inner = inner
        self._schema = schema
        self._backend_label = backend_label

    def invoke(self, messages):
        try:
            result = self._inner.invoke(messages)
        except Exception as exc:
            normalized = normalize_structured_exception(self._backend_label, exc)
            raise normalized from exc
        return ensure_structured_result(
            self._schema,
            result,
            backend_label=self._backend_label,
        )


class _FriendlyStructuredChat:
    """Wrap API-key chat models so structured-output failures are actionable."""

    def __init__(self, inner, backend_label: str):
        self._inner = inner
        self._backend_label = backend_label

    def with_structured_output(self, schema):
        return _FriendlyStructured(
            self._inner.with_structured_output(schema),
            schema,
            self._backend_label,
        )

    def invoke(self, messages):
        return self._inner.invoke(messages)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _with_friendly_structured_errors(chat, backend_label: str):
    original = chat.with_structured_output

    def with_structured_output(schema, *args, **kwargs):
        return _FriendlyStructured(
            original(schema, *args, **kwargs),
            schema,
            backend_label,
        )

    object.__setattr__(chat, "with_structured_output", with_structured_output)
    return chat


def get_llm(
    tier: str,
    *,
    temperature: float = 0,
    max_tokens: int = 2000,
    timeout: int | None = None,
    structured_retries: int | None = None,
):
    """依分層與『當前後端』回傳設定好的 chat model（含重試）。"""
    backend = settings.current_backend()
    if backend == "claude_cli":
        from app.llm_cli import CLAUDE_TIER_MODELS, ClaudeCLIChat

        choice = settings.cli_model("claude_cli")
        model = CLAUDE_TIER_MODELS[tier] if choice == "auto" else choice
        return LangWrapper(ClaudeCLIChat(
            model,
            max_tokens=max_tokens,
            timeout=timeout or 300,
            structured_retries=structured_retries or 3,
        ))
    if backend == "codex_cli":
        from app.llm_cli import CodexCLIChat
        choice = settings.cli_model("codex_cli")
        return LangWrapper(CodexCLIChat(tier, max_tokens=max_tokens,
                            model=None if choice == "auto" else choice,
                            timeout=timeout or 300,
                            structured_retries=structured_retries or 3))
    if backend == "agy_cli":
        from app.llm_cli import AgyCLIChat
        choice = settings.cli_model("agy_cli")
        return LangWrapper(AgyCLIChat(model=None if choice == "auto" else choice,
                          max_tokens=max_tokens,
                          timeout=timeout or 300,
                          structured_retries=structured_retries or 3))
    if backend == "openai":
        # BYOK：OpenAI 相容端點（OpenAI / DeepSeek / Gemini / Ollama / vLLM…）。
        from langchain_openai import ChatOpenAI
        kwargs = dict(model=settings.byok_model() or "gpt-4o-mini",
                      temperature=temperature, max_tokens=max_tokens, max_retries=4)
        if timeout is not None:
            kwargs["timeout"] = timeout
        if settings.byok_base_url():
            kwargs["base_url"] = settings.byok_base_url()
        if settings.byok_api_key():
            kwargs["api_key"] = settings.byok_api_key()
        return LangWrapper(_with_friendly_structured_errors(ChatOpenAI(**kwargs), "API key 後端"))
    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = dict(
            model=get_model(tier),
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=4,
        )
        if timeout is not None:
            kwargs["timeout"] = timeout
        return LangWrapper(_with_friendly_structured_errors(ChatAnthropic(**kwargs), "Anthropic API"))
    raise ValueError(f"unknown LLM_BACKEND: {backend!r}")


def research_structured(schema, messages, tier: str = "standard"):
    """若當前後端有內建上網工具（目前為 claude_cli 的 WebSearch/WebFetch），用之做結構化
    研究並回傳驗證後的模型；後端不支援則回 None，由呼叫端自行降級（如 Tavily / 一般知識）。"""
    backend = settings.current_backend()
    if backend == "claude_cli":
        from app.llm_cli import CLAUDE_TIER_MODELS, run_claude_structured_research

        return run_claude_structured_research(schema, messages, CLAUDE_TIER_MODELS[tier])
    return None
