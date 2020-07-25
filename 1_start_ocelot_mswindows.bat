@echo off
color 1F & ^
echo ********************************************************************* & ^
echo. & ^
echo.   Starting Ocelot, an Opacity Storage client. & ^
echo.   If this is your first time running this script & ^
echo.   this process will take some time, 10-40 minutes, & ^
echo.   depending on your network speed and computer hardware. & ^
echo. & ^
echo.   This script builds and runs the Docker containers required & ^
echo.   to use Ocelot. & ^
echo. & ^
echo.   IMPORTANT! If Docker is not installed, this script will fail. & ^
echo.   Please cancel (ctrl + c) this script and install Docker first. & ^
echo.
echo.   The easiest way to get started is to install Docker Desktop. & ^
echo.   See here for details: https://docs.docker.com/desktop/ & ^
echo. & ^
echo.   To learn more about Docker, visit: https://docs.docker.com/ & ^
echo. & ^
echo.   Once the application is ready, it will open your default browser & ^
echo.   to http://localhost:5000/ which is the link to Ocelot. & ^
echo. & ^
echo ********************************************************************* & ^
echo. & ^
echo.   Press any key to skip this step. Waiting so you have time to read message above. & ^
echo. 
timeout 60
echo. & ^
echo.   Running Docker build. & ^
echo.
docker-compose -f docker-compose.yml build
echo. & ^
echo.   Stopping Ocelot services if currently running. & ^
echo.
docker-compose stop
echo. & ^
echo.   Starting Ocelot. & ^
echo.
docker-compose -f docker-compose.yml up -d --remove-orphans
echo. & ^
echo.   Let's give the web server a few seconds to get going before trying to load Ocelot home page. & ^
echo.   Press any key to skip this step. & ^
echo.   If page doesn't load right away once open in browser, simply press F5 to refresh page.
timeout 10
start /max http://localhost:5000/
stop