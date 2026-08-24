@echo off
echo Actualizando repositorio de GitHub...
echo.

cd /d %~dp0

git add .
git commit -m "Actualizacion del bot de Discord - %date:~0,4%%Y%%m%%d% %time:~0,2%%H%%M%"
git push

echo.
echo Repositorio actualizado exitosamente!
echo.
pause