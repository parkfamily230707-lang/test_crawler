# run.sh 파일 내용 아래와 같이 프로그램을 백그라운드에서 수행하도록 명령어 지정
# >nohup ./run.sh &

set -e  # <--- 이 명령어를 추가하면 에러 발생 시 즉시 종료됨


echo "작업시작"
python ./plan_goods/plan_goods.py 202511305556569 1000
python ./plan_goods/plan_goods.py 202511305557569 1000

echo "작업끝"