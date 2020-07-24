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
echo.   and load the Ocelot home page. & ^
echo. & ^
echo ********************************************************************* & ^
echo. & ^
echo.   Press any key to skip this step. Waiting so you have time to read message above. & ^
echo. 
timeout 60
echo. & ^
echo. & ^
echo.   Ensure docker daemon is running (for those using Docker Toolbox) & ^
echo.
docker-machine start default
echo. & ^
echo.   Running Docker build. & ^
echo.
docker-compose build
echo. & ^
echo.   Stopping Ocelot services if currently running. & ^
echo.
docker-compose stop
echo. & ^
echo.   Starting Ocelot. & ^
echo.
docker-compose up -d --remove-orphans
echo. & ^
echo.
for /F "tokens=* USEBACKQ" %%F in (`docker-machine ip`) do (
set ip=%%F
)
echo.
echo.   start /max http://%ip%:5000/ & ^
echo.
echo.   Let's give the web server a few seconds to get going before trying to load Ocelot home page. & ^
echo.   Press any key to skip this step. & ^
echo.   If page doesn't load right away once open in browser, simply press F5 to refresh page.
timeout 10
echo.
start /max http://%ip%:5000/
stop