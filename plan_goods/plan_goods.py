import requests
import sys
import webbrowser
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 기본 조회 횟수
DEFAULT_COUNT = 1000 

def extract_s2b_info(estimate_code):
    """
    S2B 물품 상세 페이지에서 정보를 추출하는 함수
    """
    base_url = "https://www.s2b.kr/S2BNCustomer/rema100No.do"
    params = {
        'forwardName': 'detail',
        'f_re_estimate_code': estimate_code
    }
    
    full_detail_url = f"{base_url}?forwardName=detail&f_re_estimate_code={estimate_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        result = {
            'code': estimate_code,
            'detail_link': full_detail_url,
            'success': True
        }

        # 1. 네비게이션 텍스트 (카테고리)
        icon_src = "/S2BNCustomer/S2B/scrweb/images/remu/icon_navi_view.gif"
        icon_img = soup.find('img', attrs={'src': icon_src})
        result['navi_text'] = icon_img.parent.get_text(strip=True) if icon_img else ""

        # 2. 폰트 내용 추출 (1번째: 제목, 2번째: 등록번호)
        font_tags = soup.find_all('font', class_='f12_b_black')
        result['font_content_1'] = font_tags[0].get_text(strip=True) if len(font_tags) >= 1 else ""
        result['font_content_2'] = font_tags[1].get_text(strip=True) if len(font_tags) >= 2 else ""

        # 3. 이미지 URL 추출
        td_img_container = soup.find('td', class_='detail_img', height='276')
        if td_img_container:
            detail_img = td_img_container.find('img')
            if detail_img and 'src' in detail_img.attrs:
                result['image_url'] = urljoin("https://www.s2b.kr", detail_img['src'])
            else:
                result['image_url'] = ""
        else:
            result['image_url'] = ""

        return result

    except Exception as e:
        return {
            'code': estimate_code,
            'success': False,
            'error_msg': str(e)
        }

def create_html_report(data_list, start_code, search_count):
    """
    HTML 파일 생성 함수
    - 자바스크립트(JS)를 포함시켜 테이블 헤더 클릭 시 정렬 기능 추가
    """
    
    rows_html = ""
    for data in data_list:
        if data['success']:
            img_html = f'<img src="{data["image_url"]}" class="product-img">' if data.get('image_url') else '<span class="no-data">이미지 없음</span>'
            title = data.get('font_content_1', '-')
            category = data.get('navi_text', '-')
            reg_no = data.get('font_content_2', '-')
            link = data.get('detail_link')
            
            if not title and not category and not reg_no:
                 title = "<span style='color:#999'>(정보 없음)</span>"
            
            row = f"""
            <tr>
                <td>{img_html}</td>
                <td class="text-left">{title}</td>
                <td>{category}</td>
                <td>
                    <a href="{link}" target="_blank" title="상세보기">
                        {reg_no}
                    </a>
                </td>
            </tr>
            """
        else:
            row = f"""
            <tr style="background-color: #fff0f0;">
                <td colspan="4" style="color: red;">
                    [{data['code']}] 조회 실패: {data['error_msg']}
                </td>
            </tr>
            """
        rows_html += row

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>S2B 결과 ({start_code} 외 {search_count-1}건)</title>
        <style>
            body {{ font-family: 'Malgun Gothic', 'Dotum', sans-serif; padding: 20px; background-color: #f9f9f9; }}
            h2 {{ color: #333; }}
            .info-text {{ margin-bottom: 10px; color: #666; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background-color: #fff;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                text-align: center;
                vertical-align: middle;
            }}
            /* 정렬 기능을 위한 헤더 스타일 변경 */
            th {{
                background-color: #4a90e2;
                color: white;
                font-weight: bold;
                padding: 15px 10px;
                cursor: pointer; /* 마우스 오버 시 손가락 모양 */
                user-select: none; /* 텍스트 선택 방지 */
            }}
            th:hover {{
                background-color: #357abd; /* 마우스 오버 시 색상 변경 */
            }}
            .product-img {{
                width: 127px;
                height: 127px;
                object-fit: contain;
                display: block;
                margin: 0 auto;
                border: 1px solid #eee;
            }}
            .text-left {{ text-align: left; padding-left: 20px; }}
            .no-data {{ color: #ccc; font-size: 0.9em; }}
            a {{ text-decoration: none; color: #1a0dab; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
            tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <h2>?? S2B 물품 연속 조회 결과</h2>
        <div class="info-text">
            - 시작번호: <b>{start_code}</b><br>
            - 조회개수: <b>{search_count}개</b><br>
            <span style="font-size:0.9em; color:#888;">※ 테이블 헤더를 클릭하면 정렬할 수 있습니다.</span>
        </div>
        <table id="resultTable">
            <colgroup>
                <col width="150px" />
                <col width="*" />
                <col width="20%" />
                <col width="20%" />
            </colgroup>
            <thead>
                <tr>
                    <!-- 클릭 시 sortTable 함수 호출 (0번 컬럼부터 시작) -->
                    <th onclick="sortTable(0)">이미지 ?</th>
                    <th onclick="sortTable(1)">제목 ?</th>
                    <th onclick="sortTable(2)">카테고리 ?</th>
                    <th onclick="sortTable(3)">S2B등록번호 ?</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <!-- 테이블 정렬 스크립트 -->
        <script>
        function sortTable(n) {{
            var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
            table = document.getElementById("resultTable");
            switching = true;
            dir = "asc"; // 초기 정렬 방향: 오름차순

            while (switching) {{
                switching = false;
                rows = table.rows;
                // 헤더를 제외한 모든 행 반복
                for (i = 1; i < (rows.length - 1); i++) {{
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[n];
                    y = rows[i + 1].getElementsByTagName("TD")[n];

                    var xContent = x.innerText.toLowerCase();
                    var yContent = y.innerText.toLowerCase();

                    if (dir == "asc") {{
                        if (xContent > yContent) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }} else if (dir == "desc") {{
                        if (xContent < yContent) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }}
                }}
                if (shouldSwitch) {{
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                }} else {{
                    if (switchcount == 0 && dir == "asc") {{
                        dir = "desc";
                        switching = true;
                    }}
                }}
            }}
        }}
        </script>
    </body>
    </html>
    """
    
    file_name = f"plan_goods_{start_code}_{search_count}.txt"
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    full_path = "file://" + os.path.realpath(file_name)
    # 자동수행 주석---------------------------------------------------------------------------------------------------------------------------
    # webbrowser.open(full_path)
    print(f"\n? 결과 파일 생성 완료: {file_name}")

# --- 메인 실행부 ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("[경고] 조회할 시작 번호를 입력하지 않았습니다.")
        print(f"사용법: python s2b_plan_goods.py [시작번호] [조회횟수(선택)]")
        print(f"예  시: python s2b_plan_goods.py 202511295546579 50")
        print("=" * 60)
        sys.exit(1)

    start_number_str = sys.argv[1]
    
    if len(sys.argv) >= 3:
        try:
            search_count = int(sys.argv[2])
        except ValueError:
            print("오류: 조회 횟수는 숫자여야 합니다.")
            sys.exit(1)
    else:
        search_count = DEFAULT_COUNT
        print(f"※ 조회 횟수를 입력하지 않아 기본값({DEFAULT_COUNT}회)으로 실행합니다.")

    if not start_number_str.isdigit():
        print("오류: 시작 번호는 숫자만 입력해야 합니다.")
        sys.exit(1)
        
    start_number = int(start_number_str)
    all_results = []
    
    print(f"?? [{start_number_str}] 부터 {search_count}건 조회를 시작합니다...")
    print("-" * 50)

    for i in range(search_count):
        current_code = str(start_number + i)
        print(f"[{i+1}/{search_count}] 조회중... (번호: {current_code})", end='\r')
        data = extract_s2b_info(current_code)
        all_results.append(data)
    
    print(f"\n{'-' * 50}")
    print("수집 완료! 결과 리포트를 생성합니다.")
    
    create_html_report(all_results, start_number_str, search_count)