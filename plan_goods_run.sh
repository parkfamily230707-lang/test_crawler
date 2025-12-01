#!/bin/bash
# 파이썬 수행 코드에서 파라미터를 plan_goods_param.txt에서 읽어오도록 sh수정함.
# python ./plan_goods/plan_goods.py 202512015564458 1000
# python ./plan_goods/plan_goods.py goods_num       count

set -e  # 에러 발생 시 즉시 종료

# 설정 파일 경로
PARAM_FILE="plan_goods_param.txt"

# -----------------------------------------------------------
# 1. 파라미터 파일에서 값 읽어오기
# -----------------------------------------------------------
if [ ! -f "$PARAM_FILE" ]; then
    echo "Error: $PARAM_FILE 파일이 존재하지 않습니다."
    exit 1
fi

# goods_num 읽기 (예: 202512015564458)
CURRENT_NUM=$(grep "^goods_num=" "$PARAM_FILE" | cut -d'=' -f2 | tr -d '[:space:]')
# count 읽기 (예: 10)
COUNT_VAL=$(grep "^count=" "$PARAM_FILE" | cut -d'=' -f2 | tr -d '[:space:]')

# 값 확인
if [ -z "$CURRENT_NUM" ] || [ -z "$COUNT_VAL" ]; then
    echo "Error: 파라미터 파일에 goods_num 또는 count 값이 없습니다."
    exit 1
fi

echo "읽은 파라미터 -> goods_num: $CURRENT_NUM, count: $COUNT_VAL"

# -----------------------------------------------------------
# 2. 프로그램 수행 (파라미터 2개 전달)
# -----------------------------------------------------------
echo "작업시작 (Python 실행)"

# 파이썬 스크립트에 파라미터 전달
python ./plan_goods/plan_goods.py "$CURRENT_NUM" "$COUNT_VAL"

echo "작업끝"

# -----------------------------------------------------------
# 3. 값 계산 (+ count) 및 파일 업데이트
# -----------------------------------------------------------

# [핵심 변경 사항]
# 기존 값에 count 값만큼 더하기
NEXT_NUM=$((CURRENT_NUM + COUNT_VAL))

echo "다음 파라미터 계산: $CURRENT_NUM + $COUNT_VAL = $NEXT_NUM"

# 파일 내용을 새로 작성
# 1. goods_num은 계산된 새 값으로 저장
echo "goods_num=$NEXT_NUM" > "$PARAM_FILE"
# 2. count는 기존 값 그대로 유지 (또는 필요시 변경 가능)
echo "count=$COUNT_VAL" >> "$PARAM_FILE"

echo "파일 업데이트 완료: $PARAM_FILE"