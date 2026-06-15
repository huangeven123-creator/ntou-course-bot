import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

def parse_max_quota(quota_str: str) -> int:
    """
    Parse max quota string like '40加10', '40／10', or '不限'.
    """
    quota_str = quota_str.strip()
    if not quota_str:
        return 0
        
    # 如果有斜線，表示 上限／下限，只取前面那個
    if '/' in quota_str or '／' in quota_str:
        parts = re.split(r'[/／]', quota_str)
        quota_str = parts[0]
        
    parts = re.findall(r'\d+', quota_str)
    if not parts:
        return 999999
        
    return sum(int(p) for p in parts)


def parse_current_quota(quota_str: str) -> int:
    """
    Parse current enrolled count.
    """
    quota_str = quota_str.strip()
    parts = re.findall(r'\d+', quota_str)
    if not parts:
        return 0
    return int(parts[0])

async def query_courses(course_codes: list) -> dict:
    """
    Query details for a list of course codes in parallel using Playwright.
    Returns:
        dict: {
            "B33035PR": {
                "name": "進階英文與專業寫作",
                "teacher": "...",
                "time": "106,107",
                "classroom": "CLS412",
                "quota": 12,
                "max_quota": 50,
                "error": None
            }
        }
    """
    if not course_codes:
        return {}

    results = {}
    
    async with async_playwright() as p:
        print(f"Launching headless browser to check {len(course_codes)} courses in parallel...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        async def query_single_course(code: str):
            code = code.upper().strip()
            print(f"Worker started for course code: {code}...")
            page = await context.new_page()
            outer_url = "https://ais.ntou.edu.tw/outside.aspx?mainPage=LwBBAHAAcABsAGkAYwBhAHQAaQBvAG4ALwBUAEsARQAvAFQASwBFADIAMgAvAFQASwBFADIAMgAxADUAXwAuAGEAcwBwAHgAPwBwAHIAbwBnAGMAZAA9AFQASwBFADIAMgAxADUA"
            
            try:
                await page.goto(outer_url, wait_until="domcontentloaded", timeout=20000)
                
                # Wait for mainFrame to be registered in page.frames
                main_frame = None
                for _ in range(100): # max wait 10 seconds
                    for frame in page.frames:
                        if frame.name == "mainFrame":
                            main_frame = frame
                            break
                    if main_frame:
                        break
                    await asyncio.sleep(0.1)
                
                if not main_frame:
                    print(f"Error: mainFrame not found for {code}!")
                    results[code] = {
                        "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                        "quota": 0, "max_quota": 0, "error": "mainFrame not found"
                    }
                    await page.close()
                    return
                
                # 1. Wait for tab-2 (關鍵字查詢) selector and click it
                tab_selector = 'a[href="#tabs-2"]'
                await main_frame.wait_for_selector(tab_selector, timeout=10000)
                await main_frame.click(tab_selector)
                
                # 2. Fill keyword
                await main_frame.wait_for_selector("#Q_CH_LESSON", timeout=5000)
                await main_frame.fill('#Q_CH_LESSON', code)
                
                # 3. Select '課號' radio button (value="0")
                await main_frame.click('input[name="radioButtonClass"][value="0"]')
                
                # 4. Select '精準' query mode (value="0")
                await main_frame.click('input[name="radioButtonQuery"][value="0"]')
                
                # 5. Click Search
                await main_frame.click('#QUERY_BTN7')
                
                # Wait for results page
                await asyncio.sleep(2)
                
                # 6. Parse DataGrid from frame content
                content = await main_frame.content()
                if "查無符合資料" in content or "查無" in content:
                    print(f"Course {code} not found on server (查無符合資料).")
                    results[code] = {
                        "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                        "quota": 0, "max_quota": 0, "error": "Course not found"
                    }
                    await page.close()
                    return
                
                soup = BeautifulSoup(content, "html.parser")
                grid = soup.find(id="DataGrid")
                if not grid:
                    results[code] = {
                        "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                        "quota": 0, "max_quota": 0, "error": "DataGrid not found"
                    }
                    await page.close()
                    return
                    
                rows = grid.find_all("tr")
                if len(rows) <= 1:
                    results[code] = {
                        "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                        "quota": 0, "max_quota": 0, "error": "No course rows"
                    }
                    await page.close()
                    return
                    
                # Parse baseline data from parent row
                cols = [td.get_text(strip=True) for td in rows[1].find_all("td")]
                if len(cols) < 13:
                    results[code] = {
                        "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                        "quota": 0, "max_quota": 0, "error": "Invalid course row format"
                    }
                    await page.close()
                    return
                    
                course_name = cols[3]
                teacher = cols[6]
                quota = parse_current_quota(cols[11])
                max_quota = parse_max_quota(cols[12])
                
                # Click course code link to open popup
                await main_frame.click('#DataGrid_ctl02_COSID')
                
                # Wait for the inner details frame (contains TKE2240_03.aspx but not mainframe_open.aspx)
                detail_frame = None
                for _ in range(30):
                    for f in page.frames:
                        if 'TKE2240_03.aspx' in f.url and 'mainframe_open.aspx' not in f.url:
                            detail_frame = f
                            break
                    if detail_frame:
                        break
                    await asyncio.sleep(0.1)
                
                time_str = ""
                classroom = ""
                if detail_frame:
                    try:
                        await detail_frame.wait_for_selector("#M_SEG", timeout=3000)
                        popup_content = await detail_frame.content()
                        popup_soup = BeautifulSoup(popup_content, "html.parser")
                        
                        def get_span_text(span_id):
                            span = popup_soup.find(id=span_id)
                            return span.get_text(strip=True) if span else ""
                            
                        course_name = get_span_text("M_CH_LESSON_CURRI_EXPL") or course_name
                        teacher = get_span_text("M_LECTR_TCH_CH") or teacher
                        time_str = get_span_text("M_SEG")
                        classroom = get_span_text("M_CLSSRM_ID")
                    except Exception as inner_ex:
                        print(f"Error parsing details popup for {code}: {inner_ex}")
                
                results[code] = {
                    "name": course_name,
                    "teacher": teacher,
                    "time": time_str,
                    "classroom": classroom,
                    "quota": quota,
                    "max_quota": max_quota,
                    "error": None
                }
                print(f"Successfully scraped {code}: {course_name}, teacher={teacher}, time={time_str}, quota={quota}/{max_quota}")
                
            except Exception as ex:
                print(f"Error querying course {code}: {ex}")
                results[code] = {
                    "name": "未知課程", "teacher": "", "time": "", "classroom": "",
                    "quota": 0, "max_quota": 0, "error": str(ex)
                }
            finally:
                await page.close()
                
        # Run queries sequentially to prevent rate limiting, connection blocks and timeout on school server
        for code in course_codes:
            await query_single_course(code)
        await browser.close()
        
    return results
