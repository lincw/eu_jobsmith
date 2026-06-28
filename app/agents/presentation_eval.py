"""簡報面試題 Agent：分析簡報並以 HR 和 Group Leader 角度產生提問。"""
from app.llm import get_llm
from app.models import PresentationAssessment, Profile
import json

EVAL_SYSTEM = (
    "你是資深科技業招募顧問。請分析以下候選人準備的面試簡報文字內容，"
    "並分別以『HR (人資)』、『Group Leader (用人主管)』及『CEO (執行長)』的角色，針對簡報內容提出可能的問題。\n"
    "HR 通常關注：文化契合度、溝通能力、動機、過往經驗的反思、以及團隊合作。\n"
    "Group Leader 通常關注：技術深度、解決問題的方法、專案的具體貢獻、面臨困難的應對、以及專業領域的見解。\n"
    "CEO 通常關注：大局觀、商業影響力、策略對齊、長遠願景、以及如何幫助公司成長。\n"
    "請提供：一段簡報總結(summary)，以及列出可能的問題清單(questions)，每題標明角色(hr, leader 或 ceo)、問題內容(question)以及考量點(reason)。\n"
    "全程使用繁體中文。"
)

def evaluate_presentation(presentation_text: str, profile: Profile | None = None, jd: str | None = None, lang: str = "zh-TW") -> PresentationAssessment:
    """簡報提問分析。"""
    llm = get_llm("deep", max_tokens=6000, timeout=120, structured_retries=1).with_structured_output(PresentationAssessment)
    
    context = []
    if jd and jd.strip():
        context.append(f"【應徵職缺描述】\n{jd}")
    if profile:
        profile_json_str = profile.model_dump_json(exclude_none=True, indent=2)
        context.append(f"【候選人背景】\n{profile_json_str}")
        
    context_str = "\n\n".join(context)
    if context_str:
        context_str = f"\n\n附加參考資訊：\n{context_str}\n\n(提示：若有提供上述參考資訊，請將提問與候選人背景或職缺需求做連結，讓問題更具針對性。)\n"

    human = f"【簡報全文】\n{presentation_text}{context_str}"
    lang_instruction = "全程使用繁體中文。" if not lang.startswith("en") else "Please output the entire report in English."
    system_prompt = EVAL_SYSTEM.replace("全程使用繁體中文。", lang_instruction)
    return llm.invoke([("system", system_prompt), ("human", human)])
