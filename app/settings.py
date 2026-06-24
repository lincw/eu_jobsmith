"""集中管理環境變數、模型分層、與『可切換的 LLM 後端』。"""
import os

from dotenv import load_dotenv

load_dotenv()  # 從 .env 載入 ANTHROPIC_API_KEY、LLM_BACKEND 等

# 模型分層：依任務難度選模型，集中於此便於切換與成本控制。
MODEL_TIERS: dict[str, str] = {
    "cheap": "claude-haiku-4-5-20251001",   # 單純抽取（解析）
    "standard": "claude-sonnet-4-6",        # 匹配/生成主力
    "deep": "claude-opus-4-8",              # Critic/Supervisor 硬判斷
}


def get_model(tier: str) -> str:
    """取得某分層對應的 model id；未知分層丟 KeyError。"""
    return MODEL_TIERS[tier]


# 可選後端：以本機 CLI 訂閱為主（claude_cli / codex_cli，使用者可在 UI 切換，免 API key、
# 不吃額度，仿 open-design）；anthropic 為 API key 後端（雲端/部署可選）。
SUPPORTED_BACKENDS: tuple[str, ...] = ("claude_cli", "codex_cli", "anthropic")

BACKEND_LABELS: dict[str, str] = {
    "claude_cli": "Claude Code CLI（訂閱）",
    "codex_cli": "Codex CLI（訂閱）",
    "anthropic": "Anthropic API（金鑰）",
}

# 啟動時的後端（.env 的 LLM_BACKEND；預設本機 claude_cli）。執行期可由 set_backend 切換。
_current_backend: str = os.environ.get("LLM_BACKEND", "claude_cli")


def current_backend() -> str:
    """目前作用中的 LLM 後端。"""
    return _current_backend


def set_backend(name: str) -> None:
    """切換 LLM 後端（供 UI 設定用）；只接受 SUPPORTED_BACKENDS。"""
    global _current_backend
    if name not in SUPPORTED_BACKENDS:
        raise ValueError(f"unsupported backend: {name!r}（可選：{', '.join(SUPPORTED_BACKENDS)}）")
    _current_backend = name
