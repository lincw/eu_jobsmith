"""LinkedIn：免登入 guest jobs API（低頻、personal 用，與 104 同立場）。

端點 jobs-guest/.../seeMoreJobPostings/search 回傳職缺卡 HTML，免登入。
本機對 linkedin.com 憑證鏈驗證失敗（同 yourator/cake），故 verify=False 取公開唯讀資料。
"""
from __future__ import annotations

from urllib.parse import quote

from bs4 import BeautifulSoup

from app.models import JobPosting, SearchResult
from app.sources.base import clean, http_get

NAME = "linkedin"
SEARCHABLE = True
_API = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        "?keywords={kw}&location=Taiwan&start=0")


def search(keywords: str, limit: int = 15) -> SearchResult:
    try:
        r = http_get(_API.format(kw=quote(keywords)), verify=False)
        if not r.ok:
            return SearchResult(source=NAME, blocked=True, error=f"HTTP {r.status_code}")
    except Exception as e:  # 連線/憑證錯誤 → 降級
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    soup = BeautifulSoup(r.text, "html.parser")
    jobs: list[JobPosting] = []
    for card in soup.select("div.base-card"):
        title_el = card.select_one(".base-search-card__title")
        if not title_el:
            continue
        comp_el = card.select_one(".base-search-card__subtitle")
        loc_el = card.select_one(".job-search-card__location")
        link_el = card.select_one("a.base-card__full-link")
        url = ((link_el.get("href") if link_el else "") or "").split("?")[0]
        jobs.append(JobPosting(
            source=NAME,
            title=clean(title_el.get_text(strip=True)),
            company=clean(comp_el.get_text(strip=True)) if comp_el else "",
            location=clean(loc_el.get_text(strip=True)) if loc_el else None,
            url=url,
            snippet=None,
        ))
        if len(jobs) >= limit:
            break
    if not jobs:
        return SearchResult(source=NAME, blocked=True, error="解析不到職缺")
    return SearchResult(source=NAME, jobs=jobs)
