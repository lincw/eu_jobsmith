"""XING：免登入搜尋。"""
from __future__ import annotations

from urllib.parse import quote
from playwright.sync_api import sync_playwright

from app.models import JobPosting, SearchResult
from app.sources.base import clean

NAME = "xing"


def search(keywords: str, limit: int = 15, pages: int = 1,
           area: list[str] | None = None, location: str = "",
           date_filter: str = "any", work_type: str = "any") -> SearchResult:
    """搜尋 XING；使用 Playwright 來處理客戶端渲染及繞過防爬蟲。"""
    loc_param = f"&location={quote(location)}" if location else ""
    
    wt_param = ""
    if work_type == "remote" or work_type == "remote_hybrid":
        wt_param = "&remote=true"
        
    jobs: list[JobPosting] = []
    seen: set[str] = set()
    cap = limit * max(1, pages)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page_obj = context.new_page()

            for page in range(max(1, pages)):
                url = f"https://www.xing.com/jobs/search?keywords={quote(keywords)}{loc_param}{wt_param}&page={page + 1}"
                try:
                    page_obj.goto(url, wait_until="domcontentloaded", timeout=15000)
                    # wait for at least one search result
                    page_obj.wait_for_selector("[data-testid='job-search-result']", timeout=10000)
                except Exception as e:
                    if page == 0:
                        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])
                    break

                cards = page_obj.locator("[data-testid='job-search-result']")
                count = cards.count()
                before = len(jobs)
                
                for i in range(count):
                    card = cards.nth(i)
                    title_el = card.locator("h3, h2").first
                    if title_el.count() == 0:
                        continue
                    
                    raw_title = title_el.inner_text()
                    title = clean(raw_title)
                    
                    a_tag = card.locator("a").filter(has_text=raw_title).first
                    if a_tag.count() == 0:
                        a_tag = card.locator("a").first
                        
                    href = a_tag.get_attribute("href") if a_tag.count() > 0 else ""
                    url_str = f"https://www.xing.com{href}" if href and href.startswith("/") else href
                    url_str = url_str.split("?")[0] if url_str else ""
                    
                    key = url_str or title
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    
                    # Extract Company and Location from card text blocks
                    # Usually it's: Title \n Company \n Location
                    lines = [ln.strip() for ln in card.inner_text().split('\n') if ln.strip()]
                    comp_name = ""
                    loc_name = ""
                    try:
                        title_idx = lines.index(raw_title)
                        if title_idx + 1 < len(lines):
                            comp_name = lines[title_idx + 1]
                        if title_idx + 2 < len(lines):
                            loc_name = lines[title_idx + 2]
                    except ValueError:
                        pass
                    
                    jobs.append(JobPosting(
                        source=NAME,
                        title=title,
                        company=clean(comp_name) if comp_name else "",
                        location=clean(loc_name) if loc_name else None,
                        url=url_str,
                        snippet=None,
                    ))
                    if len(jobs) >= cap:
                        break
                        
                if len(jobs) >= cap or len(jobs) - before == 0:
                    break
                    
            browser.close()
            
    except Exception as e:
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    if not jobs:
        return SearchResult(source=NAME, blocked=True, error="解析不到職缺 (No jobs extracted)")
    return SearchResult(source=NAME, jobs=jobs)
