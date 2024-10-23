# wrtn-data-pipeline

> 과제 기간 : 24년 10월 21일
- result 파일 누락으로 23일 재제출 드립니다.

### 결과물
- app/main.py : 실행 코드
- data/dump.sql : DB dump 파일
- data/result.csv : 각 테이블의 첫 10개 row가 담긴 csv파일 (wrtn_characters)
    - 카테고리 기준 별 10개 추출했습니다. (카테고리 테이블은 categories.csv로 저장했습니다)

### 실행 방법
* 컨테이너 실행
```
# 컨테이너 실행
docker-compose up --build
# 백그라운드에서 실행
docker-compose up -d
```
* 코드를 로컬에서 실행할 경우
1. mysql-container를 띄운다.
2. app/util/datebase.py 파일에서 create_connection 메서드에서 connection의 host를 "localhost"로 변경한다.
3. app/etl/character.py에서 crawling_character_by_category browser = await p.chromium.launch(headless=False) headless 설정을 변경해주면 GUI로 크롤링되는 모습을 확인할 수 있다.
4. poetry 의존성 설치
    ```
    curl -sSL https://install.python-poetry.org | python3 -
    poetry install
    ```

5. 함수를 실행시킨다.
    ```
    python3 app/main.py
    ```

### 참고 사항
- 수집 대상량이 없어 첫실행 시 300건씩 수집했습니다. (302건 : 2건 idx를 잘못 카운팅했습니다 ,, )
    - 변경하고싶으시다면, `crawling_character_by_category` 함수의 `pagination["limit"]`를 수정하시면 됩니다.
- 카테고리 "전체"는 의도적으로 배제했습니다.
- 수집된 사항이 DB에 존재할 경우 이전 실행의 마지막 수집건과 name, author가 같을 경우 수집을 중지하도록 했습니다.
- 데이터 수집 시점과 DOM에 접근시점이 달랐던 문제가 있어, wait, state, load 등 대기 조건이 존재합니다. (수집 속도가 빠르진 않음)
- 각 정보가 원하는대로 들어가있는지 체크하는 테스트코드 필수 (이해하지 못했습니다.)

