import asyncio
import playwright
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from util.database import create_connection
import os
import sys, time

load_dotenv()
WRTN_URL = os.getenv("WRTN_URL")

def crawling_category_wrapper(category: tuple):
    try:
        print("카테고리 기준 크롤링 시작")
        conn = create_connection() # mysql 연결
        asyncio.run(crawling_character_by_category(conn, category)) 
        conn.close()
    except Exception as e:
        print(e)


async def crawling_character_by_category(conn, target_category: tuple) :
    """
    Category 기준으로 캐릭터를 추출한다.
    """
    
    target_category_id, target_category_name = target_category # 목표하는 category 값
    print(f"================ {target_category_name} 카테고리 프로세스 시작 ==================")
    
    # 가장 최근 DB에 저장된 데이터 조회 (중복 방지를 위해)
    recent_character = select_recent_character(conn, target_category_id)
    
    async with async_playwright() as p:
        """
        브라우저 OPEN 
        - 낱개의 프로세스
        """
        browser = await p.chromium.launch(headless=True) # False (크롬 브라우저 띄우기)
        page = await browser.new_page()
        await page.goto(WRTN_URL) 
        await page.wait_for_load_state("networkidle")
        
        await page.wait_for_selector("div.css-1fzkvcn", state='visible')
        categories = await page.query_selector_all('div.css-1fzkvcn div')
        
        """
        카테고리를 선택하기 위한 로직
        - 카테고리를 선택할 때, 페이지 로딩 문제로 지연이 있을 수 있어, 재시도 5회까지 반복한다.
        """
        max_retries, retries, success = 5, 0, False
        while retries < max_retries and not success:
            try:         
                for category in categories:
                    await page.wait_for_selector("p", state='visible')
                    categroy_name_element = await category.query_selector("p")
                    category_name = await categroy_name_element.text_content()
                    
                    if (target_category_name == category_name):
                        for _ in range(5):
                            try:
                                if await category.is_visible():
                                    await category.scroll_into_view_if_needed()
                                    await category.click()
                                    await page.wait_for_load_state('load')
                                    success = True
                                    break
                            except Exception:
                                print(f"[WARN] {target_category_name} 클릭 실패 시도")
                            if success:
                                break
                    
            except Exception:
                retries += 1
                print(f"[WARN] {retries}/{max_retries} :: 카테고리에 일치한 요소가 존재하지 않습니다.")
                if retries >= max_retries:
                    print("[ERROR] 카테고리 선택을 위한 최대 재시도 횟수를 초과합니다. 프로세스를 종료합니다.")
                    await browser.close()
                    sys.exit()                   
        """
        카테고리 선택 후 크롤링 시작 로직
        """
        await page.wait_for_load_state('networkidle')
        retries = 0
        idx = 0
        pagination = {"batch_size" : 100, "batch_count" : 0, "limit" : 300} # 초기 데이터 300건 수집
    
        check = set()
        chunk_data = list()
        
        while retries < max_retries:
            try:
                if await handle_error_page(page):
                    continue
                # 크롤링 로직!!
                await scrolling_character_by_category(conn, page, target_category_id, recent_character, idx, check, chunk_data, pagination) # 크롤링 코드
                break
            except Exception as e:
                retries += 1
                print(f"[WARN] {retries}/{max_retries} :: (오류 함수 : scrolling_character_by_category) 크롤링 중 오류 발생: {e}")
                if retries >= max_retries:
                    print("[ERROR] 최대 재시도 횟수 추가 :: (오류 함수 : scrolling_character_by_category)")
                
        await browser.close()

async def handle_error_page(page):
    try:
        content = await page.content()
        if "앗, 이런!" in content:
            print("[ERROR] 오류 페이지가 감지되었습니다. 페이지를 새로고침합니다.")
            await page.reload()
            await page.wait_for_load_state("load")
            return True
    except Exception as e:
        print(f"[ERROR] 페이지 처리 중 오류가 발생했습니다: {e}")
    return False
        


async def scrolling_character_by_category(conn, page, category_id, recent_character, idx, check, chunk_data, pagination):
    """
    카테고리 반복해서 스크롤 내리기
    """
    
    flag = True
    while flag:
        # data-index element 갱신
        await page.wait_for_selector('div[data-index]', state='attached')
        elements = await page.query_selector_all('div[data-index]') #data-index 갱신
        
        if not elements:
            print("[DONE] 더 이상 크롤링할 요소가 없습니다.")
            break

        for element in elements:
            data_index = await element.get_attribute('data-index')
            data_index = int(data_index)
        
            # 이미 처리한 인덱스 건너뛰기
            if data_index in check :
                continue

            # 캐릭터 엘리먼트 로드
            max_retries, retries, success = 5, 0, False
            while retries < max_retries and not success :
                try: 
                    element = await page.wait_for_selector(f'div[data-index="{data_index}"]', state='attached', timeout = 5000)
                    success = True
                except playwright._impl._errors.TimeoutError:
                    retries += 1
                    print(f"[WARN] {retries}/{max_retries} :: 카테고리 {category_id}번 카테고리의 {data_index} element 조회를 재시도합니다.")
                if retries >= max_retries:
                    print(f"[ERROR] :: div[data-index='{data_index}']를 찾기 위한 Timeout")
                    # 에러 파일 만든다면 누락된 data-index 기록
                    break
                
            if not success:
                continue
            
            # 캐릭터 정보 크롤링
            character_information = await get_character_information(page, data_index, category_id) 
            
            if character_information is None:
                continue
            
            # 캐릭터가 이전에 수집한 데이터와 일치하거나 초기값을 넘으면 종료한다.
            if recent_character is not None :
                if (recent_character[0] == character_information["name"] and recent_character[2] == character_information["author"]) : 
                    flag = False
                    break
            else:
                # 이전에 크롤링한게 없다는 가정
                if len(check) > pagination["limit"] : 
                    flag = False
                    break
    
            print(f"[{category_id}/{data_index}] : {character_information["name"]} - {character_information["author"]} ")
            # chunk 넣기
            check.add(data_index)
            chunk_data.append(character_information)
            idx = max(idx, data_index)  # 인덱스 갱신
            
            if len(chunk_data) % pagination["batch_size"] == 0:
                chunk_data, pagination = insert_chunk_data(conn, chunk_data, pagination)
            
        # 다음 스크롤
        await page.wait_for_selector("#character-explore-scroll")
        await page.evaluate("document.querySelector('#character-explore-scroll').scrollBy(0, 500)")
        await asyncio.sleep(3)  # 페이지 로드 대기
    
    # chunk_data가 남아있다면 추가로 넣기 
    if chunk_data:
        chunk_data, pagination = insert_chunk_data(conn, chunk_data, pagination)

    check.clear()
    print(f"[INFO] {category_id}의 페이지 크롤링이 완료되었습니다.")


def insert_chunk_data(conn, chunk_data, pagination):
    insert_bulk_data(conn, chunk_data)
    pagination["batch_count"] += 1
    print(f"[INFO] 남아있는 데이터 {len(chunk_data)}개 처리했습니다.")
    chunk_data.clear()
    return chunk_data, pagination


async def get_character_information(page, data_index, category_id) : 
    """
    캐릭터 정보 추출하기    
    """
    max_retries, retries, success = 5, 0, False
    charater_info = {}
    while retries < max_retries and not success: 
        try: 
            await page.wait_for_load_state('load')
            await page.wait_for_selector(f'div[data-index="{data_index}"]', state='attached')
            character_elements = await page.query_selector(f'div[data-index="{data_index}"]')
            
            # 이름 추출
            name_element = await character_elements.query_selector("p.css-sjt0pv")
            name = await name_element.text_content()
            
            # desciption
            description_element = await character_elements.query_selector("p.css-9xnb32")
            description = await description_element.text_content()

            # author
            author_element = await character_elements.query_selector("p.css-uoinwu")
            author = await author_element.text_content()
            
            # image
            image_element = await character_elements.query_selector("img")
            image = await image_element.get_attribute("src")

            # message
            # message = await get_character_message(data_index, page, character_elements)
            await character_elements.click()
            await page.wait_for_load_state('load')
            
            # "대화하기 메세지 클릭"
            await page.wait_for_selector('button.css-1a5bwx8', state='visible')
            message_button = await page.query_selector('button.css-1a5bwx8')
            await message_button.click()
            
            # 문장 크롤링
            await page.wait_for_selector('div.css-1ff969x', state='visible')
            message_contents = await page.query_selector('div.css-1ff969x')
            message_list = await message_contents.query_selector_all('p')
            message = "\n".join([await message.text_content() for message in message_list])
            
            # 원래 페이지로 돌아가기
            await page.go_back()
            
            # 결과
            charater_info =  {
                "name" : name if name else None, 
                "description": description if description else None, 
                "image" : image if image else None,
                "message" : message if message else None,
                "author" : author if author else None, 
                "category" : category_id if category_id else None}
            success = True
            
        except Exception as e:
            retries += 1
            print(f"[WARN] {retries}/{max_retries} :: {data_index}번 캐릭터 정보를 수집하는 데 실패했습니다.")
            if retries >= max_retries:
                print(f"[ERROR] 최대 재시도 실패 :: data_index : {data_index}")
                break
            
    return charater_info if success else None

def insert_bulk_data(conn, chunk_data) :
    cursor = conn.cursor()
    
        # 데이터 삽입 쿼리
    insert_query = """
    INSERT INTO wrtn_characters (name, description, author, image_url, category, created_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    
    # 데이터 여러 개를 한 번에 삽입
    data_list = [(data["name"], data["description"], data["author"], data["image"], data["category"]) for data in chunk_data]
    cursor.executemany(insert_query, data_list)
    
    # 트랜잭션 완료
    conn.commit()
    print(f"{len(chunk_data)}개의 데이터를 DB에 삽입했습니다.")


def select_recent_character(conn, category_id: int):
    cursor = conn.cursor()
    
    # 쿼리 작성 및 실행
    query = f"""
    SELECT name, description, author
    FROM wrtn_characters
    WHERE category = {category_id}
    ORDER BY created_at
    LIMIT 1;
    """
    
    cursor.execute(query)
    result = cursor.fetchone()
    
    return result