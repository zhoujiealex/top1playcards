@echo off
echo "��ʼ��װ������..."
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple  -r  %~dp0/requirements.txt
rem pip install -r  %~dp0/requirements.txt
pause
