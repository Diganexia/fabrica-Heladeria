@echo off
echo Limpiando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Generando ejecutable...
pyinstaller heladeria.spec

echo.
if exist dist\Heladeria.exe (
    echo BUILD EXITOSO: dist\Heladeria.exe
) else (
    echo ERROR: no se encontro el ejecutable
)
pause
