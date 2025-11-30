# run.sh 파일 내용 아래와 같이 프로그램을 백그라운드에서 수행하도록 명령어 지정
# >nohup ./run.sh &
echo "작업시작"
python ./plan_goods/plan_goods.py 202511305554580 10
python ./plan_goods/plan_goods.py 202511305554590 10
echo "작업끝"