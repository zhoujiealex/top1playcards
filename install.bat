@echo off
echo "开始安装依赖包..."
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple  -r  %~dp0/requirements.txt
pause
