import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
from datetime import datetime

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 설정 구간
# ==========================================
URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
START_DATE = "20240101"
END_DATE = datetime.today().strftime("%Y%m%d")
OUTPUT_FILE = "s2b_result.xlsx"
DEBUG_HTML_FILE = "debug_response.html" # 서버 응답을 저장할 파일명

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.s2b.kr/S2BNCustomer/tcmo001.do",
    "Origin": "https://www.s2b.kr",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def main():
    print(f"[{datetime.now()}] 크롤러 시작")
    session = requests.Session()
    
    # 1. [중요] 최초 접속하여 세션(쿠키) 생성
    print(" >> 1. 메인 페이지 접속하여 쿠키 획득 중...")
    try:
        session.get(URL, headers=HEADERS, verify=False, timeout=30)
    except Exception as e:
        print(f"접속 실패: {e}")
        return

    # 2. 데이터 요청 (POST)
    print(" >> 2. 검색 데이터 요청 중...")
    
    # 한글 파라미터가 깨질 수 있으므로, 인코딩에 주의해야 함
    # '전국' 같은 한글이 들어가면 EUC-KR 서버에서 에러가 날 수 있으므로
    # 일단 지역 조건 없이 조회해봅니다.
    data = {
        'forwardName': 'list03',
        'pageNo': 1,
        'tender_date_start': START_DATE,
        'tender_date_end': END_DATE,
        'process_yn': 'Y',
        'search_yn': 'Y',
        'excelSection': 'N',
        'tender_item': '',    # 전체
        'estimate_kind': '',  # 전체
        'areaKind': ''        # 전체 (한글 인코딩 문제 회피용)
    }

    try:
        response = session.post(URL, data=data, headers=HEADERS, verify=False, timeout=30)
        response.encoding = 'euc-kr' # 필수
        
        # 3. [진단] 응답 내용을 파일로 저장 (눈으로 확인하기 위함)
        print(f" >> 응답 코드: {response.status_code}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f" >> [중요] 서버 응답 화면을 '{DEBUG_HTML_FILE}'로 저장했습니다.")

        # 4. 파싱 시작
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 테이블 찾기 로직 강화
        target_table = None
        tables = soup.find_all('table')
        for t in tables:
            text = t.get_text()
            if '계약명' in text and '계약번호' in text:
                target_table = t
                break
        
        if not target_table:
            print(" >> ? 데이터 테이블을 찾지 못했습니다. (debug_response.html 파일을 확인하세요)")
            # 빈 엑셀 생성 (에러 방지)
            pd.DataFrame({'Status': ['데이터없음']}).to_excel(OUTPUT_FILE, index=False)
            return

        print(" >> 테이블 발견! 데이터 추출 중...")
        processed_rows = []
        all_trs = target_table.find_all('tr')
        
        i = 0
        while i < len(all_trs):
            tds = all_trs[i].find_all('td')
            # No 컬럼이 있는 행만 처리
            if not tds or not tds[0].get_text(strip=True).isdigit():
                i += 1
                continue
            
            if i + 1 >= len(all_trs): break
            tds2 = all_trs[i+1].find_all('td')
            
            try:
                item = {
                    'No': tds[0].get_text(strip=True),
                    '계약구분': tds[1].get_text(strip=True),
                    '계약번호': tds[2].get_text(strip=True),
                    '계약명': tds[3].get_text(strip=True),
                    '금액': tds[4].get_text(strip=True),
                    '계약대상자': tds[5].get_text(strip=True),
                    '계약일': tds2[3].get_text(strip=True) if len(tds2) > 3 else ""
                }
                processed_rows.append(item)
            except:
                pass
            i += 1

        # 결과 저장
        if processed_rows:
            print(f" >> ? 총 {len(processed_rows)}건 추출 성공!")
            pd.DataFrame(processed_rows).to_excel(OUTPUT_FILE, index=False)
        else:
            print(" >> ?? 테이블은 찾았으나 추출된 행이 없습니다.")
            pd.DataFrame({'Status': ['행없음']}).to_excel(OUTPUT_FILE, index=False)

    except Exception as e:
        print(f"에러 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()