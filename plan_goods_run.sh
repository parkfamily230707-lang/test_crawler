# run.sh 파일 내용 아래와 같이 프로그램을 백그라운드에서 수행하도록 명령어 지정
# >nohup ./run.sh &

set -e  # <--- 이 명령어를 추가하면 에러 발생 시 즉시 종료됨


echo "작업시작"
python ./plan_goods/plan_goods.py 202511305554569 1000
python ./plan_goods/plan_goods.py 202511305555569 1000
python ./plan_goods/plan_goods.py 202511305556569 1000
python ./plan_goods/plan_goods.py 202511305557569 1000
python ./plan_goods/plan_goods.py 202511305558569 1000
python ./plan_goods/plan_goods.py 202511305559569 1000
python ./plan_goods/plan_goods.py 202511305560569 1000
python ./plan_goods/plan_goods.py 202511305561569 1000
python ./plan_goods/plan_goods.py 202511305562569 1000
python ./plan_goods/plan_goods.py 202511305563569 1000

python ./plan_goods/plan_goods.py 202511305564569 1000
python ./plan_goods/plan_goods.py 202511305565569 1000
python ./plan_goods/plan_goods.py 202511305566569 1000
python ./plan_goods/plan_goods.py 202511305567569 1000
python ./plan_goods/plan_goods.py 202511305568569 1000
python ./plan_goods/plan_goods.py 202511305569569 1000
python ./plan_goods/plan_goods.py 202511305570569 1000
python ./plan_goods/plan_goods.py 202511305571569 1000
python ./plan_goods/plan_goods.py 202511305572569 1000
python ./plan_goods/plan_goods.py 202511305573569 1000

echo "작업끝"