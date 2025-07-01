from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def fetch_latest_news_links(company_name, max_results=3):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    search_url = f"https://search.naver.com/search.naver?where=news&query={company_name}"
    driver.get(search_url)
    time.sleep(5)  # 렌더링 대기 시간 늘림
    # 렌더링된 HTML 저장
    with open("selenium_naver_news_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = []
    for a in soup.select('a[target="_blank"]'):
        span = a.find('span', class_='sds-comps-text-type-headline1')
        href = a.get("href")
        title = span.text.strip() if span else href
        # 썸네일 이미지 찾기 (a 태그의 부모나 조상에서 img 태그 탐색)
        img_tag = None
        parent = a.parent
        for _ in range(3):  # 최대 3단계 위까지 탐색
            if parent is None:
                break
            img_tag = parent.find('img')
            if img_tag:
                break
            parent = parent.parent
        image_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None
        # 언론사(뉴스사) 찾기 (a 태그의 조상에서 span.sds-comps-text-type-body2 등)
        source = ''
        parent = a.parent
        for _ in range(3):
            if parent is None:
                break
            source_span = parent.find('span', class_='sds-comps-text-type-body2')
            if source_span:
                source = source_span.text.strip()
                break
            parent = parent.parent
        if span and href and href.startswith("http"):
            if not any(l['url'] == href for l in links):
                links.append({'url': href, 'title': title, 'image_url': image_url, 'source': source})
        if len(links) >= max_results:
            break
    driver.quit()
    return links 