@echo off
echo ============================================
echo Git 初始化和推送到 GitHub
echo ============================================
echo.
python "%~dp0init_git.py"
echo.
echo 按任意键退出...
pause > nul
