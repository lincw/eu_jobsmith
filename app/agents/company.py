"""⑧ 公司情報 Agent：上網查證公司並彙整成 CompanyBrief。"""
from app.tools.search import search_web
from app.llm import get_llm
from app.models import CompanyBrief

COMPANY_SYSTEM = (
    "你是企業情報分析師。根據提供的公開搜尋結果，彙整出公司情報卡："
    "規模、產業、資金/募資狀況、薪資範圍、福利、文化與評價摘要、"
    "面試評價、避雷紅旗、近期新聞，並附上來源連結。"
    "只根據提供的資料作答，不要臆測；資料不足的欄位留空。"
)


def research_company(company_name: str) -> CompanyBrief:
    """查證公司並回傳 CompanyBrief（standard 分層）；查無資料則標記 data_limited。"""
    try:
        results = search_web(f"{company_name} 公司 評價 薪資 福利 面試")
    except Exception:
        results = []

    if not results:
        return CompanyBrief(company=company_name, data_limited=True)

    context = "\n\n".join(
        f"- {r['title']}\n{r['content']}\n來源: {r['url']}" for r in results
    )
    human = f"公司名稱：{company_name}\n\n公開搜尋結果：\n{context}"
    llm = get_llm("standard").with_structured_output(CompanyBrief)
    return llm.invoke([("system", COMPANY_SYSTEM), ("human", human)])
