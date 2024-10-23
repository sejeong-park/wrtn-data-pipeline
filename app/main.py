import asyncio
import time
from multiprocessing import Pool
from playwright.async_api import async_playwright

from util.database import connect_database
from etl.category import crawling_category, insert_categories
import etl.character as character

def multi_process_crwaling(category_list):
    print("멀티프로세싱 실행")
    with Pool(processes=3) as pool:
        print("낱개 프로세스 실행")
        pool.map(character.crawling_category_wrapper, category_list)


if __name__ == "__main__" : 
    """
    MAIN
    """
    conn = connect_database() 
    
    # 카테고리 저장
    category_list = asyncio.run(crawling_category())
    category_list = insert_categories(conn, category_list) # 튜플로 리스트 갱신
    print(category_list)
    # 카테고리 기준으로 멀티 프로세싱
    multi_process_crwaling(category_list)
    