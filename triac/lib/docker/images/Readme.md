## Base images

This folder contains the base images that are used by triac to execute the fuzzing against.
Each base image should adhere to the following:

1. Have a openssh server installed
    1. The server should allow login via the user 'root'
    2. The login should be done via the ssh key given in root of the 'lib/docker' folder
    3. The ssh server should run on port 22
2. A preinstalled init system (e.g. systemd)
3. Python installed in version 3.11 with all the packages given in the requirements.txt file at the root of this repository


> **Important**
> Please not that the build of the image will be performed with the repository root as context. Therefore, any path that copies files needs to relative to the repository root. (This is needed to allow copying the requirements files and ssh-keys)