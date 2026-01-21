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
# 설정 구간
# ==========================================
URL = "https://www.s2b.kr/S2BNCustomer/tcmo001.do"
RENEW_INTERVAL = 2    
LONG_PAUSE_INTERVAL = 10  
PARAM_FILE = "sell_goods_param.txt"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36"
]

log_file_handle = None

def log(msg):
    print(msg)
    if log_file_handle:
        try:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            log_file_handle.write(timestamp + str(msg) + "\n")
            log_file_handle.flush()
        except: pass

def update_param_file(date_str, page_no):
    try:
        with open(PARAM_FILE, "w", encoding="utf-8") as f:
            f.write(f"search_day={date_str}\n")
            f.write(f"page={page_no}\n")
        log(f" [기록] 파라미터 업데이트: {date_str} / {page_no}페이지")
    except Exception as e:
        log(f" [오류] 파라미터 업데이트 실패: {e}")

def get_real_browser_headers():
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
    time.sleep(random.uniform(3.0, 7.0))
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
        res.encoding = 'euc-kr' # S2B는 보통 EUC-KR 사용
        
        if res.status_code != 200:
            log(f"    ? 서버 응답 에러 (Status: {res.status_code})")
            return None, None

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [강화] 테이블 찾기 로직: '계약번호'라는 글자가 포함된 테이블을 정밀 탐색
        target_table = None
        all_tables = soup.find_all('table')
        for t in all_tables:
            t_text = t.get_text()
            if '계약명' in t_text and '계약번호' in t_text:
                # 너무 큰 상위 테이블이 잡히지 않도록 행(tr)이 있는 최소 단위 테이블 확인
                if len(t.find_all('tr')) > 2:
                    target_table = t
                    break
        
        if not target_table:
            # 테이블을 아예 못 찾은 경우 (구조 변경 의심)
            log("    [경고] 데이터 테이블을 찾을 수 없습니다. (페이지 구조 확인 필요)")
            return [], True

        page_rows = []
        all_trs = target_table.find_all('tr')
        
        i = 0
        while i < len(all_trs):
            tds = all_trs[i].find_all('td')
            # 1. 계약번호가 있는 첫 번째 행인지 확인
            if not tds or not tds[0].get_text(strip=True).isdigit():
                i += 1
                continue
            
            # 2. 다음 행(기관명/계약일)이 있는지 확인
            if i + 1 >= len(all_trs): break
            tds2 = all_trs[i+1].find_all('td')
            
            try:
                raw_contract_no = tds[2].get_text(strip=True)
                # 숫자만 남기기
                clean_no = re.sub(r'[^0-9]', '', raw_contract_no)

                # 날짜 불일치 시: 지금까지 수집한 건 반환하고 중단 신호
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
            i += 2 # 두 줄이 한 세트이므로 2씩 증가
            
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
        print(f"파라미터 읽기 오류 (파일 형식을 확인하세요): {e}")
        return
    
    # [방어] 오늘 날짜면 실행 안 함
    today_str = datetime.now().strftime("%Y%m%d")
    if target_date == today_str:
        print(f" [중단] {target_date}는 오늘 날짜이므로 수집하지 않습니다.")
        return

    output_xlsx = f"s2b_result_{target_date}.xlsx"
    output_log = f"s2b_result_{target_date}.log"

    try:
        log_file_handle = open(output_log, "a", encoding="utf-8")
    except: pass

    log("="*60)
    log(f" [시작] S2B 정밀 크롤러 (구조 보강 버전)")
    log(f" 날짜: {target_date} / 페이지: {start_page}")
    log("="*60)
    
    all_results = []
    session = requests.Session()
    current_page = start_page
    request_count = 0
    
    try:
        while True:
            log(f" >> [요청] {current_page}페이지...")
            items, is_continue = fetch_page_data(session, target_date, current_page)
            
            # 데이터 저장 로직
            if items:
                all_results.extend(items)
                log(f"    └ {len(items)}건 수집됨 (누적 {len(all_results)}건)")
                pd.DataFrame(all_results).to_excel(output_xlsx, index=False)
            
            # 날짜 변경 시
            if is_continue is False:
                log(f" !! 날짜 경계 도달. {target_date} 수집 종료.")
                curr_dt = datetime.strptime(target_date, "%Y%m%d")
                new_date = (curr_dt + timedelta(days=1)).strftime("%Y%m%d")
                update_param_file(new_date, 1)
                break

            # 에러 또는 종료 시
            if items is None:
                update_param_file(target_date, current_page)
                break
            
            if len(items) == 0:
                log("    ? 더 이상 수집할 데이터가 없습니다.")
                # 데이터가 아예 없어도 날짜는 넘어가야 한다면 아래 주석 해제
                # curr_dt = datetime.strptime(target_date, "%Y%m%d")
                # new_date = (curr_dt + timedelta(days=1)).strftime("%Y%m%d")
                # update_param_file(new_date, 1)
                break

            # 성공 시 다음 페이지 예약
            update_param_file(target_date, current_page + 1)
            current_page += 1
            request_count += 1
            
            # 휴식 로직
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