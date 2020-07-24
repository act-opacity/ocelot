#!/bin/bash
echo -e ""
echo -e "*********************************************************************"
echo -e ""
echo -e "\tStarting Ocelot, an Opacity Storage client."
echo -e "\tIf this is your first time running this script"
echo -e "\tthis process will take some time, 10-40 minutes,"
echo -e "\tdepending on your network speed and computer hardware."
echo -e 
echo -e "\tThis script builds and runs the Docker containers required"
echo -e "\tto use Ocelot."
echo -e 
echo -e "\tIMPORTANT! If Docker is not installed, this script will fail."
echo -e "\tPlease cancel (ctrl + c) this script and install Docker first."
echo -e
echo -e "\tThe easiest way to get started is to install Docker Desktop."
echo -e "\tSee here for details: https://docs.docker.com/desktop/"
echo -e
echo -e "\tDocker Desktop is not available for Linux. Install Docker Engine"
echo -e "\tusing your preferred package manager instead."
echo -e 
echo -e "\tTo learn more about Docker, visit: https://docs.docker.com/"
echo -e 
echo -e "\tOnce the application is ready, it will open your default browser"
echo -e "\tto http://localhost:5000/ which is the link to Ocelot."
echo -e
echo -e "*********************************************************************"
echo -e ""
read -n 1 -s -r -p "Press any key to continue"
echo -e ""
echo -e ""
echo -e "\tCreating OpacityDrive directory in your home directory if it doesn't yet exist."
echo -e ""
mkdir -p ~/OpacityDrive
echo -e ""
echo -e "\tRunning Docker build."
echo -e ""
docker-compose build
echo -e ""
echo -e "\tStopping Ocelot services if currently running."
echo -e ""
docker-compose stop
echo -e ""
echo -e "\tStarting Ocelot."
echo -e ""
docker-compose up -d --remove-orphans
echo -e ""
echo -e "\tServices have been restarted. Ocelot should soon be accessible"
echo -e "\tfrom your browser. If the web page is slow to load initially, simply"
echo -e "\tpress the F5 key to refresh it."
echo -e ""
read -n 1 -s -r -p "Press any key to load Ocelot in your browser"
echo -e ""
x-www-browser http://localhost:5000/