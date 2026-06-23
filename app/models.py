"""共享領域模型（強型別、可被 with_structured_output 使用）。"""
from pydantic import BaseModel, Field


class Profile(BaseModel):
    """使用者求職背景。"""
    name: str
    summary: str = Field(description="一句話自我介紹/定位")
    skills: list[str] = Field(default_factory=list)
    experiences: list[str] = Field(default_factory=list, description="經歷條列")
    education: str | None = None
    years_experience: float | None = None
    preferred_roles: list[str] = Field(default_factory=list)
    raw_text: str = Field(description="原始貼上的履歷文字")


class ParsedJob(BaseModel):
    """解析後的職缺。"""
    title: str
    company: str
    location: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    min_years: float | None = None
    tech_stack: list[str] = Field(default_factory=list)
    language: str = Field(default="zh", description="JD 主要語言: zh 或 en")
    salary: str | None = None


class MatchReport(BaseModel):
    """匹配評分報告。"""
    score: int = Field(ge=0, le=100, description="0-100 匹配分數")
    matched: list[str] = Field(default_factory=list, description="符合的項目")
    gaps: list[str] = Field(default_factory=list, description="落差/缺少的項目")
    suggestions: list[str] = Field(default_factory=list, description="補強建議")
    recommend_proceed: bool = Field(description="是否建議繼續產出投遞包")
    reason: str = Field(description="建議續做與否的理由")
