@echo off
echo ============================================
echo  RLBotPro - Build com PyInstaller/nicegui-pack
echo ============================================
echo.

REM Verificar se nicegui-pack esta instalado
pip show nicegui-pack >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando nicegui-pack...
    pip install nicegui-pack
)

echo Gerando executavel...
nicegui-pack ^
    --onefile ^
    --windowed ^
    --name "RLBotPro" ^
    --icon icone.ico ^
    --add-data "data;data" ^
    main.py

echo.
if %errorlevel% equ 0 (
    echo ============================================
    echo  Build concluido! Exe em: dist\RLBotPro.exe
    echo  Copie config.json para a mesma pasta do exe.
    echo ============================================
) else (
    echo ERRO no build. Verifique os logs acima.
)

pause
