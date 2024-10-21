import asyncio
from playwright.async_api import async_playwright
import time

async def get_character_message(page, character_elements) :
    """
    캐릭터의 상세페이지에 접속하여 메세지 추출
    """
    #  모달 띄우기
    await character_elements.click()
    await page.wait_for_load_state("load")
    
    # "대화하기 메세지 클릭"
    message_button = await page.query_selector('button.css-1a5bwx8')
    await message_button.click()
    
    # 문장 크롤링
    await page.wait_for_selector('div.css-1ff969x')
    message_contents = await page.query_selector('div.css-1ff969x')
    message_list = await message_contents.query_selector_all("p")
    message = "\n".join([await message.text_content() for message in message_list])
    
    # 원래 페이지로 돌아가기
    await page.go_back()
    
    return message

async def get_character_information(page, data_index, category) : 
    """
    캐릭터 정보 추출하기    
    """
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
    message = await get_character_message(page, character_elements)
    
    # 결과
    return {
        "name" : name, 
        "description": description, 
        "image" : image,
        "message" : message,
        "author" : author, 
        "category" : "카테고리"}

            
async def crawling_character_by_category(browser, page, category) :
    """
    특정 카테고리 반복하기
    """
    print("카테고리!!")
    await page.wait_for_load_state('networkidle') 

    
    """
    카테고리의 항목 스크롤
    """
    idx = 0
    pagnation = {"batch_size" : 100, "batch_count" : 0}
    check = set()
    chunk_data = list()
    while True:
        # data-index element 갱신
        elements = await page.query_selector_all(f'div[data-index]') #data-index 갱신
        
        if not elements:
            print("[DONE] 더 이상 크롤링할 요소가 없습니다.")
            break

        for element in elements:
            data_index = await element.get_attribute('data-index')
            data_index = int(data_index)
            # scroll_div = await page.query_selector(f'div[data-index="{data_index}"]')
            # await scroll_div.scroll_into_view_if_needed()
        
            # 이미 처리한 인덱스 건너뛰기
            if data_index in check :
                continue

            # 캐릭터 정보 크롤링
            await page.wait_for_selector(f'div[data-index="{data_index}"]', timeout = 1000)
            character_information = await get_character_information(page, data_index, category) 
            print(f"[{data_index}]  : {character_information["name"]} ")

            # chunk 넣기
            check.add(data_index)
            chunk_data.append(character_information)
            idx = max(idx, data_index)  # 인덱스 갱신
            
            # chunk 저장!
            if len(check) >= pagnation["batch_size"] :
                check.clear()
                pagnation["batch_count"] += 1
                print(chunk_data)
                print("check 클리어!!", len(chunk_data))
                
            
        # 다음 스크롤
        await page.wait_for_selector("#character-explore-scroll")
        await page.evaluate("document.querySelector('#character-explore-scroll').scrollBy(0, 500)")

async def crawling_category():
    
    async with async_playwright() as p:
        
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto('https://wrtn.ai/character/explore')  # 실제 크롤링할 URL로 변경

        await page.wait_for_selector("div.css-1fzkvcn", state='visible')
        categories = await page.query_selector_all('div.css-1fzkvcn div')
        
        # 카테고리 크롤링
        for category in categories:
            categroy_name_element = await category.query_selector("p")
            category_name = await categroy_name_element.text_content()
            print(category_name)
            # 카테고리 저장하기
            
        
        # 카테고리 기준으로 멀티 프로세싱!!!
        
        # 카테고리 기준 찾기 (이걸 하나만해야한다)
        await categories[1].click()
        await page.wait_for_timeout(1000)
        
        # charcters = await crawl_character_for_category(page)
        target_element = await page.query_selector("div.css-1iaf8e")
        if target_element:
            await target_element.scroll_into_view_if_needed()

        """
        이전 인덱스 가져오아함
        """
        await crawling_character_by_category(browser, page, categories[1])
            
        await browser.close()


# Playwright는 비동기적 방식으로 동작하므로, asyncio.run()으로 실행
asyncio.run(crawling_category())
