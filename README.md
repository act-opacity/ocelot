# Ocelot, an Opacity Storage Client Application
Ocelot is a containerized web application that interfaces with the [Opacity Storage](https://www.opacity.io/) web services. Ocelot is client software meant to be run on your local machine.

Since Ocelot uses Docker to run, it can be run on any device that supports Docker, including Windows, Macintosh (Mac) and Linux.

Ocelot is Free and Open-Source Software (FOSS). See License below.

Ocelot featured capabilities:
* Store and manage multiple Opacity accounts
* Reliably sync your files (upload, download) and folders both directions between Opacity and one or more of your devices
* Provide a sync status per file to know where it resides (Opacity, local machine, both)
* Enable you to search and filter your files easily in one big table
* Allow you to perform file and folder management activities (create, delete, rename, move)
* Review file version history and access previous file versions
* Quickly open a file's share link to share or review its contents

## Install Ocelot

#### Installation Dependencies: Docker
The Docker Engine and the Docker CLI client are required to be installed on your machine (Windows, Mac, Linux).

For Windows and Mac users, installing **Docker Desktop** is the easiest way to install the required Docker components and to have a way to manage Ocelot (start, stop, restart, remove) and monitor Ocelot (performance, logs) and its components. See instructions here: https://docs.docker.com/desktop/ .

If you have an outdated version of Windows or Mac that doesn't support Docker Desktop, you can use **the older Docker Toolbox instead**. It is not as user friendly as Docker Desktop, and additional steps will need to be taken to get things working. Specifically:
* if the Ocelot startup script mentions "docker daemon not running", you will need to determine how to start it on your machine. See this [Docker guide](https://docs.docker.com/machine/overview/) for reference.
* you will need to run **docker-machine ip** to get your Docker host IP and then replace references to "localhost" within Ocelot app components. So, for example, when Ocelot launches in the browser, you will need to replace "localhost:5000" with "192.168.99.100:5000". The provided start up script can be modified to automate this process as well.
* Windows users, the script named **5_start_ocelot_mswindows_docker-toolbox.bat** will automate these required steps to accommodate Docker Toolbox.
* Mac users, a script specifically for use with Docker Toolbox hasn't been created yet, but you can follow steps mentioned above to understand what is required.

**Linux users** may have additional required steps to take to get Docker running initially. e.g. adding your Linux username to the "docker" group.

#### Windows Users
1. Download a zip file that contains the files of this repository. Click [this link](https://github.com/act-opacity/ocelot/archive/master.zip) to start the download.
2. Unzip the downloaded file to a place you'll remember. The location will be used for starting and stopping Ocelot as needed.
3. Navigate into the unzipped directory.
4. Run the provided startup script. 
   * If you have **Docker Desktop** installed, run this startup script: **"1_start_ocelot_mswindows.bat"**
   * Otherwise, you'll need **Docker Toolbox** installed and you'll run this startup script: **"5_start_ocelot_mswindows_docker-toolbox.bat"**
     * Running either script will download and configure Ocelot and then run it.
     * This startup script can be used in the future to re-start Ocelot.
     * Creating a desktop shortcut to this script is recommended.
     * To stop Ocelot for any reason (not required), run **"2_stop_ocelot_mswindows.bat"**
5. Done!

#### Mac and Linux Users
1. Download a zip file that contains the files of this repository. Click [this link](https://github.com/act-opacity/ocelot/archive/master.zip) to start the download.
2. Unzip the downloaded file to a place you'll remember. The location will be used for starting and stopping Ocelot as needed.
3. Navigate into the unzipped directory.
4. Run/double click the file (startup script) named **"3_start_ocelot_mac_linux.sh"**
   * Doing so will download and configure Ocelot and then run it.
   * This file can be used in the future to re-start Ocelot.
   * To stop Ocelot for any reason (not required), run **"4_stop_ocelot_mac_linux.sh"**
5. Done!

## Other Notes Related to Installing and Running Ocelot
* The first time you run the startup script, it will take a while because it is downloading the required images and libraries.
* The next time you run the startup script (as needed, in the future), Ocelot will start up in about 15-20 seconds.
* Ocelot will continue to run in the background unless Docker is stopped intentionally.
* Closing the browser does not stop Ocelot from running. The browser is simply a way to interact with Ocelot.
* You can also use Docker Desktop (dashboard) to start and stop Ocelot, review logs, connect to and inspect containers, etc.
* Ocelot expects a directory named **OpacityDrive** to be located in your home directory. The startup script will create this directory automatically.
  * OpacityDrive for Windows will be located here: C:\Users\\<your_username>\\OpacityDrive
  * OpacityDrive for Mac/Linux will be located here: /home/<your_username>/OpacityDrive

## License
Ocelot is [licensed](https://github.com/act-opacity/ocelot/blob/master/LICENSE) under the Apache License, Version 2.0.
