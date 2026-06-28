"""Indeed：免登入搜尋。"""
from __future__ import annotations

from urllib.parse import quote
from playwright.sync_api import sync_playwright

from app.models import JobPosting, SearchResult
from app.sources.base import clean

NAME = "indeed"


def search(keywords: str, limit: int = 15, pages: int = 1,
           area: list[str] | None = None, location: str = "",
           date_filter: str = "any", work_type: str = "any") -> SearchResult:
    """搜尋 Indeed；使用 Playwright 來處理客戶端渲染及繞過防爬蟲。"""
    loc_param = f"&l={quote(location)}" if location else ""
    
    date_param = ""
    if date_filter == "past_week":
        date_param = "&fromage=7"
    elif date_filter == "past_month":
        date_param = "&fromage=14"  # Indeed commonly uses 14 as max or defaults to it
    elif date_filter == "past_24h":
        date_param = "&fromage=1"
        
    wt_param = ""
    if work_type == "remote" or work_type == "remote_hybrid":
        wt_param = "&sc=0kf%3Aattr%28DSQF7%29%3B"
    # Indeed does not have a straightforward URL parameter for hybrid across all locales.
        
    jobs: list[JobPosting] = []
    seen: set[str] = set()
    cap = limit * max(1, pages)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page_obj = context.new_page()

            for page in range(max(1, pages)):
                url = f"https://www.indeed.com/jobs?q={quote(keywords)}{loc_param}&start={page * 10}{date_param}{wt_param}"
                try:
                    page_obj.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page_obj.wait_for_selector("div.job_seen_beacon", timeout=10000)
                except Exception as e:
                    if page == 0:
                        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])
                    break

                cards = page_obj.locator("div.job_seen_beacon")
                count = cards.count()
                before = len(jobs)
                
                for i in range(count):
                    card = cards.nth(i)
                    
                    title_el = card.locator(".jobTitle").first
                    if title_el.count() == 0:
                        continue
                    title = clean(title_el.inner_text())
                    
                    a_tag = card.locator(".jobTitle a").first
                    href = a_tag.get_attribute("href") if a_tag.count() > 0 else ""
                    
                    url_str = f"https://www.indeed.com{href}" if href and href.startswith("/") else href
                    url_str = url_str.split("?")[0] if url_str else ""
                    
                    key = url_str or title
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    
                    comp_el = card.locator("[data-testid='company-name']").first
                    loc_el = card.locator("[data-testid='text-location']").first
                    
                    jobs.append(JobPosting(
                        source=NAME,
                        title=title,
                        company=clean(comp_el.inner_text()) if comp_el.count() > 0 else "",
                        location=clean(loc_el.inner_text()) if loc_el.count() > 0 else None,
                        url=url_str,
                        snippet=None,
                    ))
                    if len(jobs) >= cap:
                        break
                        
                if len(jobs) >= cap or len(jobs) - before == 0:
                    break
                    
            if not jobs:
                with open("indeed_dump.html", "w", encoding="utf-8") as f:
                    f.write(page_obj.content())
            browser.close()
    except Exception as e:
        return SearchResult(source=NAME, blocked=True, error=str(e)[:150])

    if not jobs:
        return SearchResult(source=NAME, blocked=True, error="解析不到職缺 (No jobs extracted)")
    return SearchResult(source=NAME, jobs=jobs)
