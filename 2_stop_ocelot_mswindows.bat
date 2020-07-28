@echo off
color 1F & ^
echo ********************************************************************* & ^
echo. & ^
echo.   Shutting down all Ocelot services now. & ^
echo.   If you ran this script by mistake, simply close this window now. & ^
echo. & ^
echo.   To restart Ocelot again, run 1_start_ocelot_mswindows.bat & ^
echo. & ^
echo ********************************************************************* & ^
timeout 10
docker-compose stop
exit