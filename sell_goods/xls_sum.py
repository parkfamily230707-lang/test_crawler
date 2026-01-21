import pandas as pd
import glob
import os
import re


print("페이지별로 분리된 엑셀파일을 날짜별로 합칩니다.")

# 1. 설정
input_path = './'  # 엑셀 파일들이 있는 폴더 경로
output_path = './combined/'  # 합쳐진 파일이 저장될 폴더
if not os.path.exists(output_path):
    os.makedirs(output_path)

# 2. 대상 파일 목록 가져오기 (xlsx 기준)
file_list = glob.glob(os.path.join(input_path, "*.xlsx"))

# 3. 날짜별로 파일 그룹화
date_groups = {}
for file_path in file_list:
    filename = os.path.basename(file_path)
    
    # 파일명에서 8자리 숫자(날짜) 추출 (예: 20251101)
    match = re.search(r'\d{8}', filename)
    if match:
        date = match.group()
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(file_path)

# 4. 그룹별로 합치기 실행
for date, files in date_groups.items():
    print(f"{date} 날짜 파일 합치는 중: {len(files)}개")
    
    combined_data = []
    for file in files:
        df = pd.read_excel(file)
        combined_data.append(df)
    
    # 데이터 통합
    final_df = pd.concat(combined_data, ignore_index=True)
    
    # 결과 저장 (예: s2b_result_20251101.xlsx)
    output_filename = f"s2b_result_{date}.xlsx"
    final_df.to_excel(os.path.join(output_path, output_filename), index=False)
    print(f"-> 생성 완료: {output_filename}")

print("모든 날짜별 통합 작업이 완료되었습니다.")