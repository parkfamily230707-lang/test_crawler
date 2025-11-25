import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
import traceback
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

# 브라우저 위장 헤더 강화
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.s2b.kr/S2BNCustomer/tcmo001.do",
    "Origin": "https://www.s2b.kr",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def check_connection(session):
    """접속 테스트 및 IP 차단 여부 진단"""
    print("\n[진단] 사이트 접속 테스트 중...")
    try:
        res = session.get(URL, headers=HEADERS, verify=False, timeout=20)
        res.encoding = 'euc-kr'
        print(f"[진단] 응답 코드: {res.status_code}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('title')
        print(f"[진단] 페이지 제목: {title.get_text().strip() if title else '제목 없음'}")
        
        if "Access Denied" in res.text or res.status_code == 403:
            print("[진단] ? 경고: 사이트에서 접근을 차단했습니다 (IP 차단 가능성 높음).")
            return False
        return True
    except Exception as e:
        print(f"[진단] ? 접속 실패: {e}")
        return False

def get_page_data(session, page_no):
    print(f" >> 페이지 {page_no} 요청 중...")
    
    data = {
        'forwardName': 'list03',
        'pageNo': page_no,
        'tender_date_start': START_DATE,
        'tender_date_end': END_DATE,
        'process_yn': 'Y',
        'search_yn': 'Y',
        'excelSection': 'N',
        'tender_item': '',
        'estimate_kind': '',
        'areaKind': '전국'
    }

    try:
        response = session.post(URL, data=data, headers=HEADERS, verify=False, timeout=30)
        response.encoding = 'euc-kr'
        
        if response.status_code != 200:
            print(f"Error: 페이지 요청 실패 (Status: {response.status_code})")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 데이터 테이블 찾기 (class="td_dark_line" 중 '계약명'이 있는 것)
        tables = soup.find_all('table', class_='td_dark_line')
        target_table = None
        
        for t in tables:
            if 'searchArea' in str(t.attrs.get('id', '')): continue
            if '계약명' in t.get_text():
                target_table = t
                break
        
        if not target_table:
            # 테이블을 못 찾으면 소스 일부를 출력해 원인 파악
            print("Warning: 결과 테이블을 찾을 수 없습니다. HTML 구조가 변경되었거나 데이터가 없습니다.")
            return []

        processed_rows = []
        all_trs = target_table.find_all('tr')
        
        i = 0
        while i < len(all_trs):
            tr = all_trs[i]
            tds = tr.find_all('td')
            
            # 첫 번째 칸이 숫자인지 확인 (No)
            if not tds or not tds[0].get_text(strip=True).isdigit():
                i += 1
                continue
            
            # 짝이 맞는 다음 행(tr2) 확인
            if i + 1 >= len(all_trs): break
            tr2 = all_trs[i+1]
            tds2 = tr2.find_all('td')
            
            try:
                # 데이터 매핑
                item = {
                    'No': tds[0].get_text(strip=True),
                    '계약구분': tds[1].get_text(strip=True),
                    '계약번호': tds[2].get_text(strip=True),
                    '계약명': tds[3].get_text(strip=True),
                    '금액': tds[4].get_text(strip=True),
                    '계약대상자': tds[5].get_text(strip=True),
                    '거래구분': tds2[0].get_text(strip=True) if tds2 else "",
                    '기관명': tds2[1].get_text(strip=True) if len(tds2) > 1 else "",
                    '견적요청일': tds2[2].get_text(strip=True) if len(tds2) > 2 else "",
                    '계약일': tds2[3].get_text(strip=True) if len(tds2) > 3 else ""
                }
                processed_rows.append(item)
            except Exception as e:
                print(f"Row parsing error: {e}")
                
            i += 1 

        return processed_rows

    except Exception as e:
        print(f"Error on page {page_no}:")
        traceback.print_exc()
        return []

def main():
    print(f"[{datetime.now()}] 크롤러 시작")
    session = requests.Session()
    
    # 1. 접속 가능 여부 진단
    if not check_connection(session):
        print("? 서버 접속 불가로 크롤링을 중단합니다.")
        # 빈 엑셀 파일 생성 (GitHub Actions 에러 방지용)
        pd.DataFrame({'Status': ['접속실패']}).to_excel(OUTPUT_FILE, index=False)
        return

    all_data = []
    page_no = 1
    
    # 테스트를 위해 최대 3페이지까지만 수집 (잘 되면 숫자 늘리세요)
    while page_no <= 3:
        items = get_page_data(session, page_no)
        
        if not items:
            print(f"페이지 {page_no} 데이터 없음. 수집 종료.")
            break
            
        all_data.extend(items)
        print(f" >> 누적 수집: {len(all_data)} 건")
        
        # 무한 루프 방지용 (중복 체크)
        if len(all_data) > len(items) * 2:
             if all_data[-1]['No'] == all_data[-1 - len(items)]['No']:
                 print("중복 데이터 감지. 종료.")
                 break
        
        page_no += 1
        time.sleep(1)

    # 결과 저장
    if all_data:
        print(f"? 총 {len(all_data)}건 수집 완료. 엑셀 저장 중...")
        df = pd.DataFrame(all_data)
        df.to_excel(OUTPUT_FILE, index=False)
    else:
        print("?? 수집된 데이터가 0건입니다. (빈 파일 생성)")
        pd.DataFrame({'Status': ['데이터없음']}).to_excel(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    main()