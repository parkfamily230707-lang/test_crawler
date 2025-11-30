import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# [설정] 기본값 설정
# ==========================================
DEFAULT_START_DATE = "20251124"
DEFAULT_END_DATE = "20251124"
OUTPUT_FILE = "s2b_result.xlsx"

URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.s2b.kr/S2BNCustomer/tcmo001.do",
    "Origin": "https://www.s2b.kr",
    "Content-Type": "application/x-www-form-urlencoded"
}

def get_data_for_period(session, start_str, end_str):
    """특정 기간(3개월 이내)의 데이터를 페이지별로 수집"""
    print(f" >> 조회 진행 중: {start_str} ~ {end_str}")
    
    period_data = []
    page_no = 1
    
    while True:
        data = {
            'forwardName': 'list03',
            'pageNo': page_no,
            'tender_date_start': start_str,
            'tender_date_end': end_str,
            'process_yn': 'Y',
            'search_yn': 'Y',
            'excelSection': 'N',
            'tender_item': '',
            'estimate_kind': '',
            'areaKind': ''
        }
        
        try:
            res = session.post(URL, data=data, headers=HEADERS, verify=False, timeout=30)
            res.encoding = 'euc-kr'
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 테이블 찾기
            target_table = None
            for t in soup.find_all('table'):
                if '계약명' in t.get_text() and '계약번호' in t.get_text():
                    target_table = t
                    break
            
            if not target_table:
                break

            # 데이터 파싱
            rows_found = False
            all_trs = target_table.find_all('tr')
            
            i = 0
            while i < len(all_trs):
                tds = all_trs[i].find_all('td')
                
                if not tds or not tds[0].get_text(strip=True).isdigit():
                    i += 1
                    continue
                
                rows_found = True
                
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
                        '기관명': tds2[1].get_text(strip=True) if len(tds2) > 1 else "",
                        '계약일': tds2[3].get_text(strip=True) if len(tds2) > 3 else ""
                    }
                    period_data.append(item)
                except:
                    pass
                
                i += 1

            if not rows_found:
                break
                
            print(f"    └ 페이지 {page_no}: {len(period_data)}건 누적됨")
            
            # ====================================================
            # [테스트용 코드] 3페이지까지만 수집하고 중단
            # ====================================================
            if page_no >= 3:
                print("    ? [테스트 모드] 3페이지만 수집하고 다음 구간으로 넘어갑니다.")
                break
            # ====================================================
            
            page_no += 1
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"    └ 통신 에러 발생: {e}")
            break
            
    return period_data

def main():
    parser = argparse.ArgumentParser(description='S2B Crawler')
    parser.add_argument('--start', type=str, default=DEFAULT_START_DATE, help='시작일')
    parser.add_argument('--end', type=str, default=DEFAULT_END_DATE, help='종료일')
    args = parser.parse_args()

    start_date_str = args.start
    end_date_str = args.end

    print("="*60)
    print(f" S2B 학교장터 크롤러 (TEST MODE: Max 3 Pages)")
    print(f" 대상 기간: {start_date_str} ~ {end_date_str}")
    print("="*60)
    
    session = requests.Session()
    try:
        session.get(URL, headers=HEADERS, verify=False, timeout=20)
    except:
        print("? 서버 초기 접속 실패")
        return

    all_results = []
    
    curr_date = datetime.strptime(start_date_str, "%Y%m%d")
    final_end_date = datetime.strptime(end_date_str, "%Y%m%d")
    
    while curr_date <= final_end_date:
        next_date = curr_date + relativedelta(months=3) - timedelta(days=1)
        if next_date > final_end_date:
            next_date = final_end_date
            
        s_chunk = curr_date.strftime("%Y%m%d")
        e_chunk = next_date.strftime("%Y%m%d")
        
        chunk_data = get_data_for_period(session, s_chunk, e_chunk)
        all_results.extend(chunk_data)
        
        curr_date = next_date + timedelta(days=1)
        if curr_date <= final_end_date:
            time.sleep(1)

    print("="*60)
    if all_results:
        print(f" ? 총 {len(all_results)}건 수집 완료!")
        try:
            df = pd.DataFrame(all_results)
            df.to_excel(OUTPUT_FILE, index=False)
            print(f" ?? 파일 저장 완료: {os.path.abspath(OUTPUT_FILE)}")
        except Exception as e:
            print(f" ? 엑셀 저장 실패: {e}")
    else:
        print(" ?? 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()