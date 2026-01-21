import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
import random
import re
from datetime import datetime, timedelta

# SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# [중요] 경로 설정 보강
# ==========================================
# 실행 중인 파일(sell_goods.py)이 있는 폴더를 기준으로 경로를 고정합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
RENEW_INTERVAL = 2    
LONG_PAUSE_INTERVAL = 10  
PARAM_FILE = os.path.join(BASE_DIR, "sell_goods_param.txt")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36"
]

log_file_handle = None

def log(msg):
    """콘솔 및 파일 로그 기록"""
    print(msg)
    if log_file_handle:
        try:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            log_file_handle.write(timestamp + str(msg) + "\n")
            log_file_handle.flush()
        except: pass

def update_param_file(date_str, page_no):
    """파라미터 파일(txt) 업데이트"""
    try:
        with open(PARAM_FILE, "w", encoding="utf-8") as f:
            f.write(f"search_day={date_str}\n")
            f.write(f"page={page_no}\n")
        log(f" [기록] 파라미터 업데이트: {date_str} / {page_no}페이지")
    except Exception as e:
        log(f" [오류] 파라미터 업데이트 실패: {e}")

def get_real_browser_headers():
    """랜덤 User-Agent 포함 헤더 생성"""
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Referer": "https://www.s2b.kr/S2BNCustomer/tcmo001.do",
        "Origin": "https://www.s2b.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Connection": "keep-alive"
    }

def fetch_page_data(session, date_str, page_no):
    """특정 페이지 데이터를 수집하고 날짜 검증"""
    time.sleep(random.uniform(10.0, 20.0))
    data = {
        'forwardName': 'list03',
        'pageNo': str(page_no),
        'tender_date_start': date_str,
        'tender_date_end': date_str,
        'process_yn': 'Y',
        'search_yn': 'Y',
        'excelSection': 'N'
    }
    
    try:
        headers = get_real_browser_headers()
        res = session.post(URL, data=data, headers=headers, verify=False, timeout=30)
        res.encoding = 'euc-kr'
        
        if res.status_code != 200:
            log(f"    ? 서버 응답 에러 (Status: {res.status_code})")
            return None, None

        soup = BeautifulSoup(res.text, 'html.parser')
        target_table = None
        for t in soup.find_all('table'):
            t_text = t.get_text()
            if '계약명' in t_text and '계약번호' in t_text:
                if len(t.find_all('tr')) > 2:
                    target_table = t
                    break
        
        if not target_table:
            log("    [경고] 데이터 테이블을 찾을 수 없습니다.")
            return [], True

        page_rows = []
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
                raw_contract_no = tds[2].get_text(strip=True)
                clean_no = re.sub(r'[^0-9]', '', raw_contract_no)

                if not clean_no.startswith(date_str):
                    return page_rows, False 

                item = {
                    'No': tds[0].get_text(strip=True),
                    '계약구분': tds[1].get_text(strip=True),
                    '계약번호': raw_contract_no,
                    '계약명': tds[3].get_text(strip=True),
                    '금액': tds[4].get_text(strip=True),
                    '계약대상자': tds[5].get_text(strip=True),
                    '기관명': tds2[1].get_text(strip=True) if len(tds2) > 1 else "",
                    '계약일': tds2[3].get_text(strip=True) if len(tds2) > 3 else ""
                }
                page_rows.append(item)
            except: pass
            i += 2
            
        return page_rows, True

    except Exception as e:
        log(f"    ? 예외 발생: {e}")
        return None, None

def main():
    global log_file_handle

    if not os.path.exists(PARAM_FILE):
        print(f"오류: {PARAM_FILE} 파일이 없습니다.")
        return

    try:
        with open(PARAM_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            target_date = re.search(r'search_day=(\d+)', content).group(1)
            start_page = int(re.search(r'page=(\d+)', content).group(1))
    except Exception as e:
        print(f"파라미터 읽기 오류: {e}")
        return
    
    # [방어] 오늘 날짜면 실행 안 함
    today_str = datetime.now().strftime("%Y%m%d")
    if target_date == today_str:
        print(f" [중단] {target_date}는 오늘 날짜이므로 수집하지 않습니다.")
        return

    # [수정] 파일명 규칙: s2b_result_날짜_시작페이지.xlsx
    output_xlsx = os.path.join(BASE_DIR, f"s2b_result_{target_date}_{start_page}.xlsx")
    output_log = os.path.join(BASE_DIR, f"s2b_result_{target_date}_{start_page}.log")

    try:
        log_file_handle = open(output_log, "a", encoding="utf-8")
    except: pass

    log("="*60)
    log(f" [시작] S2B 정밀 크롤러")
    log(f" 대상 날짜: {target_date} / 시작 페이지: {start_page}")
    log(f" 저장 파일: {os.path.basename(output_xlsx)}")
    log("="*60)
    
    # 기존 데이터 불러오기 (이어쓰기 보장)
    all_results = []
    if os.path.exists(output_xlsx):
        try:
            all_results = pd.read_excel(output_xlsx).to_dict('records')
            log(f" >> [연결] 기존 파일 데이터 {len(all_results)}건 로드 완료.")
        except: pass

    session = requests.Session()
    current_page = start_page
    request_count = 0
    
    try:
        while True:
            log(f" >> [요청] {current_page}페이지...")
            items, is_continue = fetch_page_data(session, target_date, current_page)
            
            # 수집 데이터가 있다면 리스트에 추가하고 엑셀 저장
            if items:
                all_results.extend(items)
                log(f"    └ {len(items)}건 수집됨 (누적 {len(all_results)}건)")
                pd.DataFrame(all_results).to_excel(output_xlsx, index=False)
            
            # 날짜가 바뀌었을 때 (+1일 갱신 및 종료)
            if is_continue is False:
                log(f" !! 날짜 경계 도달. {target_date} 수집 완료.")
                curr_dt = datetime.strptime(target_date, "%Y%m%d")
                new_date = (curr_dt + timedelta(days=1)).strftime("%Y%m%d")
                update_param_file(new_date, 1)
                break

            # 통신 에러 시 (현재 페이지 보존)
            if items is None:
                update_param_file(target_date, current_page)
                break
            
            # 더 이상 데이터가 없을 때
            if len(items) == 0:
                log("    ? 더 이상 수집할 데이터가 없습니다.")
                break

            # 한 페이지 성공 시마다 다음 페이지 번호 기록
            update_param_file(target_date, current_page + 1)
            current_page += 1
            request_count += 1
            
            # 과부하 방지 휴식
            if request_count % LONG_PAUSE_INTERVAL == 0:
                time.sleep(random.uniform(60, 90))
                session = requests.Session()
            elif request_count % RENEW_INTERVAL == 0:
                session = requests.Session()
                time.sleep(random.uniform(5, 8))

    except Exception as e:
        log(f" [에러] {e}")
        update_param_file(target_date, current_page)

    log("="*60)
    log(" [완료] 프로세스 종료")
    if log_file_handle: log_file_handle.close()

if __name__ == "__main__":
    main()