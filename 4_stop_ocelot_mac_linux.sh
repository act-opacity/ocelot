#!/bin/bash
echo -e ""
echo -e "*********************************************************************"
echo -e ""
echo -e "\tShutting down all Ocelot services now."
echo -e "\tIf you ran this script by mistake, use ctr+c to exit."
echo -e ""
echo -e "\tTo restart Ocelot again, execute /bin/bash 3_start_ocelot_mac_linux.sh"
echo -e ""
echo -e "*********************************************************************"
echo -e ""
read -n 1 -s -r -p "Press any key to continue"
docker-compose stop