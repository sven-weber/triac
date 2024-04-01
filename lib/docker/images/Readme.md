## Base images

This folder contains the base images that are used by triac to execute the fuzzing against.
Each base image should adhere to the following:

1. Have a working folder in /usr/app/triac
2. Have a openssh server installed
    1. The server should allow login via the user 'root'
    2. The login should be done via the ssh key given in root of the 'lib/docker' folder
    3. The ssh server should run on port 22
3. A preinstalled init system (e.g. systemd)
4. Python installed in version 3.11 with all the packages given in the requirements.txt file at the root of this repository

