@echo off
REM =====================================================
REM  OSHS GUI 一键打包脚本
REM  日期: %date% %time%
REM =====================================================

echo.
echo [1/5] 激活虚拟环境...
call venv39\Scripts\activate

echo.
echo [2/5] 清理旧的 build 和 dist 文件夹...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo.
echo [3/5] 开始打包...
pyinstaller --clean --onefile --noconsole ^
--name=OSHS_GUI ^
--add-data "maplist.csv;." ^
--add-data "map_info.json;." ^
--add-data "state_machine1.json;." ^
Main.py

echo.
echo [4/5] 打包完成，检查输出文件...
if exist "dist\OSHS_GUI.exe" (
    echo ✅ 打包成功！
    echo 输出文件: dist\OSHS_GUI.exe
) else (
    echo ❌ 打包失败，请检查上方错误信息。
)

echo.
echo [5/5] 退出虚拟环境...
deactivate

echo.
pause
