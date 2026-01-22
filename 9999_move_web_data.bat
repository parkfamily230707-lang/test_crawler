@echo off
setlocal

:: 1. 이동할 파일이 있는 현재 디렉토리로 이동 (필요한 경우 수정)
:: cd /d "파일이_있는_원본_경로"

:: 2. 대상 폴더 경로 설정
set "targetDir=C:\psn\cursor\parkfamily_test_crawler\plan_goods\data"

:: 3. 대상 폴더가 없으면 생성
if not exist "%targetDir%" (
    mkdir "%targetDir%"
)

:: 4. 파일 이동 실행
:: plan_goods_2026로 시작하는 모든 파일을 대상 폴더로 이동
move "plan_goods_2026*" "%targetDir%"

echo 파일 이동이 완료되었습니다.
pause