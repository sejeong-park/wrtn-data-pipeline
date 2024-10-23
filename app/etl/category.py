import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os

load_dotenv()
WRTN_URL = os.getenv('WRTN_URL')

async def crawling_category() -> list:
    """
    카테고리 항목 조회
    """
    category_list = []
    async with async_playwright() as p:
        
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(WRTN_URL) 

        await page.wait_for_selector("div.css-1fzkvcn", state='visible')
        categories = await page.query_selector_all('div.css-1fzkvcn div')

        # 카테고리 크롤링
        for category in categories:
            categroy_name_element = await category.query_selector("p")
            category_name = await categroy_name_element.text_content()
            category_list.append(category_name)
        await browser.close()
    return category_list


def insert_categories(conn, category_list: list) -> list: 
    """
    중복을 제거하고 category를 DB에 넣는다.
    return: db의 category 테이블
    """
    cursor = conn.cursor()
    
    cursor.execute("SELECT category FROM categories")
    existing_categories = cursor.fetchall()
    
    existing_categories_set = {row[0] for row in existing_categories} # 중복제거
    for category in category_list:
        if category != "전체" and category not in existing_categories_set:
            cursor.execute("""
            INSERT INTO categories (category)
            VALUES (%s)
            """, (category, ))
            
    conn.commit()
    print("데이터베이스에 없는 카테고리를 삽입했습니다.")
    
    cursor.execute("SELECT id, category FROM categories")
    updated_categories = cursor.fetchall()
    return updated_categories