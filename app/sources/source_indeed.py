"""Indeed：免登入搜尋。"""
from __future__ import annotations

from urllib.parse import quote

from bs4 import BeautifulSoup

from app.models import JobPosting, SearchResult
from app.sources.base import clean, http_get

NAME = "indeed"


def search(keywords: str, limit: int = 15, pages: int = 1,
           area: list[str] | None = None, location: str = "") -> SearchResult:
    """搜尋 Indeed；pages>1 時逐頁抓取並跨頁去重。"""
    loc_param = f"&l={quote(location)}" if location else ""
    jobs: list[JobPosting] = []
    seen: set[str] = set()
    cap = limit * max(1, pages)
    
    for page in range(max(1, pages)):
        try:
            url = f"https://www.indeed.com/jobs?q={quote(keywords)}{loc_param}&start={page * 10}"
            r = http_get(url, verify=False)
            if not r.ok:
                if page == 0:
                    return SearchResult(source=NAME, blocked=True, error=f"HTTP {r.status_code}")
                break
        except Exception as e:
            if page == 0:
                return SearchResult(source=NAME, blocked=True, error=str(e)[:150])
            break

        soup = BeautifulSoup(r.text, "html.parser")
        before = len(jobs)
        for card in soup.select(".jobsearch-ResultsList li div.job_seen_beacon"):
            title_el = card.select_one("h2.jobTitle span[title]") or card.select_one("h2.jobTitle")
            if not title_el:
                continue
            comp_el = card.select_one("span[data-testid='company-name']")
            loc_el = card.select_one("div[data-testid='text-location']")
            link_el = card.select_one("h2.jobTitle a")
            
            href = link_el.get("href") if link_el else ""
            url_str = f"https://www.indeed.com{href}" if href.startswith("/") else href
            url_str = url_str.split("?")[0] if url_str else ""
            
            key = url_str or clean(title_el.get_text(strip=True))
            if key in seen:
                continue
            seen.add(key)
            
            jobs.append(JobPosting(
                source=NAME,
                title=clean(title_el.get_text(strip=True)),
                company=clean(comp_el.get_text(strip=True)) if comp_el else "",
                location=clean(loc_el.get_text(strip=True)) if loc_el else None,
                url=url_str,
                snippet=None,
            ))
            if len(jobs) >= cap:
                break
                
        if len(jobs) >= cap or len(jobs) - before == 0:
            break
            
    if not jobs:
        return SearchResult(source=NAME, blocked=True, error="解析不到職缺")
    return SearchResult(source=NAME, jobs=jobs)
