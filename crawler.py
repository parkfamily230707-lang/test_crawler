import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
import traceback
import re
from datetime import datetime

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 설정 구간
# ==========================================
URL_GET = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
URL_POST = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
START_DATE = "20240101"
END_DATE = datetime.today().strftime("%Y%m%d")
OUTPUT_FILE = "s2b_result.xlsx"
ERROR_FILE = "s2b_error.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.s2b.kr/S2BNCustomer/tcmo001.do",
    "Origin": "https://www.s2b.kr",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def extract_alert_message(html_text):
    """HTML 내의 자바스크립트 alert 메시지 추출"""
    match = re.search(r"alert\(['\"](.*?)['\"]\)", html_text)
    if match:
        return match.group(1)
    return "메시지 없음"

def main():
    print(f"[{datetime.now()}] 크롤러 시작")
    session = requests.Session()
    
    # 1. GET 요청으로 쿠키(JSESSIONID) 획득
    print(" >> 1. 페이지 진입 (세션 획득)...")
    try:
        res_get = session.get(URL_GET, headers=HEADERS, verify=False, timeout=30)
        res_get.encoding = 'euc-kr'
        print(f"    - 진입 응답 코드: {res_get.status_code}")
    except Exception as e:
        print(f"    - 접속 실패: {e}")
        return

    time.sleep(2) # 사람이 접속한 척 딜레이

    # 2. POST 요청 (검색)
    print(" >> 2. 검색 데이터 요청 (POST)...")
    
    # 중요: 한글이 포함되면 EUC-KR 서버에서 깨질 수 있으므로, 
    # 지역(areaKind)이나 검색어 등은 일단 비워서 보냅니다.
    data = {
        'forwardName': 'list03',
        'pageNo': 1,
        'tender_date_start': START_DATE,
        'tender_date_end': END_DATE,
        'process_yn': 'Y',
        'search_yn': 'Y',
        'excelSection': 'N',
        # 아래 값들은 비워두거나 기본값 사용
        'tender_item': '',    
        'estimate_kind': '',  
        'areaKind': ''        
    }

    try:
        response = session.post(URL_POST, data=data, headers=HEADERS, verify=False, timeout=30)
        # S2B는 반드시 euc-kr
        response.encoding = 'euc-kr'
        
        # 3. 결과 분석
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 테이블 찾기
        target_table = None
        for t in soup.find_all('table'):
            if '계약명' in t.get_text() and '계약번호' in t.get_text():
                target_table = t
                break
        
        if not target_table:
            print("\n[!!!] 결과 테이블을 찾지 못했습니다.")
            
            # 에러 메시지 추출 시도
            alert_msg = extract_alert_message(response.text)
            print(f" >> S2B 반환 메시지(Alert): {alert_msg}")
            
            # HTML 파일로 저장 (GitHub에서 확인용)
            with open(ERROR_FILE, "w", encoding="utf-8") as f:
                f.write(f"<!-- S2B Alert: {alert_msg} -->\n")
                f.write(response.text)
            print(f" >> 현재 화면을 '{ERROR_FILE}'로 저장했습니다. GitHub 파일 목록에서 확인하세요.")
            
            # 빈 엑셀 생성 (Action 에러 방지)
            pd.DataFrame({'Error': [alert_msg]}).to_excel(OUTPUT_FILE, index=False)
            return

        # 4. 데이터가 있다면 파싱
        print(f" >> 테이블 발견! 데이터 추출 중...")
        # ... (이전과 동일한 파싱 로직)
        processed_rows = []
        all_trs = target_table.find_all('tr')
        i = 0
        while i < len(all_trs):
            tds = all_trs[i].find_all('td')
            if not tds or not tds[0].get_text(strip=True).isdigit():
                i += 1
                continue
            if i + 1 >= len(all_trs): break
            tds2 = all_trs[i+1].find_all('td')
            try:
                item = {
                    'No': tds[0].get_text(strip=True),
                    '계약명': tds[3].get_text(strip=True),
                    '금액': tds[4].get_text(strip=True),
                    '계약일': tds2[3].get_text(strip=True) if len(tds2) > 3 else ""
                }
                processed_rows.append(item)
            except: pass
            i += 1

        if processed_rows:
            print(f" >> ? {len(processed_rows)}건 수집 성공")
            pd.DataFrame(processed_rows).to_excel(OUTPUT_FILE, index=False)
        else:
            print(" >> 데이터 행 없음.")
            pd.DataFrame({'Status': ['NoData']}).to_excel(OUTPUT_FILE, index=False)

    except Exception as e:
        print(f"Critical Error: {e}")
        traceback.print_exc()
        # 에러 발생 시에도 빈 파일 생성
        pd.DataFrame({'Error': ['ScriptError']}).to_excel(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    main()