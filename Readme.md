## TRIaC: A generaTion-based fuzzing framework for Resilience in Infrastructure as Code

This repository contains the supplementary material for TRiAC, a tool for generation-based fuzzing that enables unit and differential testing of IaC tools. TRIaC achieves this through the use of Docker and so-called Wrappers that enable the testing of specific modules. As of now, the tool implements fuzzing for the [Ansible](https://www.ansible.com/) [builtin.file](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/file_module.html) module. Further modules and support for [pyinfra](https://pyinfra.com/) will be added in the near future.

![Image](/img/example.png "Screenshot of a TRIaC run")

This readme provides instructions on how to use TRIaC to perform fuzzing. Instructions on how to extend the tool with new capabilities to cover more tools or modules can be found in the [triac/wrappers subfolder](/triac/wrappers/Readme.md).

> [!WARNING]  
> This tool is still under active development

# How to run TRIaC

To run TRIaC on your machine, there are two prerequisite that need to be fulfilled.

### 1. Prerequisite: Docker 

First, a recent installation of [Docker](https://www.docker.com/#build) is required. You can find instructions on how to install Docker [here](https://www.docker.com/#build). In order to communicate with Docker, TRIaC requires that the connection information for the Docker API are provided via the following environment variables. This should be the case by default for every Docker installation. If the connection should not work, you will find corresponding error messages when executing TRIaC.

| Variable          | description                                                                                   |
|-------------------|-----------------------------------------------------------------------------------------------|
| DOCKER_HOST       | The URL to the Docker host. For example unix:///var/run/docker.sock or  tcp://127.0.0.1:1234. |
| DOCKER_TLS_VERIFY | Whether to verify the host against a CA certificate                                           |
| DOCKER_CERT_PATH  | A path to a directory containing TLS certificates to use when connecting to the Docker host.  |

You can find further information [here](https://docker-py.readthedocs.io/en/stable/client.html#docker.client.from_env).

### 2. Prerequisite: Python & packages

To run TRIaC you need to have python 3 installed. Once the install is finished, you can install all of TRIaCs dependencies as follows:

```console
pip install -r requirements/prod.txt
```

If you also want to extend TRIaC/develop your own wrappers, we recommend installing the development dependencies as follows instead:

```console
pip install -r requirements/dev.txt
```

## Run TRIaC

Once the prerequisites have been fulfilled you can run TRIaC. TRIaC is a python module that can be invoked **from the root of this repository** as follows:

```console
python -m triac
```

Once started, TRIaC will begin fuzzing automatically using sensible defaults. However, there are many options available to control the fuzzing run. You can get all options via:

```console
python -m triac --help
```

For example, you can control the number of rounds and how many wrappers should be run per round. Moreover, you can specific a fixed base image or increase the log level if you need further details.

No matter which options you choose, TRIaC will generate a log file and error files for each run. See the section [Monitoring runs and reproducing errors](#monitoring-runs-and-reproducing-errors) below for further details.

### Running TRIaC repeatedly or unsupervised

If you plan on running TRIaC more than once, we recommend using the ```--keep-base-images``` option as follows:

```console
python -m triac --keep-base-images
```

Without this option, TRIaC will build all used base images for each run and cleanup the images once the run is finished. While this does not leave behind data on your machine, building the images can take some time. Therefore, if you are playing around with TRIaC or developing your own wrapper it is recommended to disable the image cleanup after the run via this option.

Moreover, if you plan on running TRIaC for a long time without supervision, it might make sense to enable ```--continue-on-error```. By default, TRIaC will stop the execution once a unexpected error is discovered. For example, an IaC execution might fail. In these cases, TRIaC will wait for the user to press any key before the execution continues. However, in long-running settings this might not be the preferred behavior. Therefore, you can let TRIaC continue without any user input by using this option as follows:

```
python -m triac --continue-on-error
```

## Monitoring runs and reproducing errors

By default, TRIaC generates the following two things for every run

### Log file

A log file is generated in the root of the repository with the name ```triac.log```. This file contains all the output visible in the TRIaC UI and enables you to go through the whole execution in your own pace. This file will adhere to the log level specified during the TRIaC execution.

### Error files

For every state mismatch (between target and actual state) that TRIaC finds, it will generate two error files. The files are located inside a ```error``` folder in the root of this repository and the file name is the timestamp when the error was found. It will generate one ```.json``` and one ```.triac``` file.

#### JSON

The JSON file offers a human readable difference between the actual and the target state. First, the file will contain a description of the whole target and actual state. Moreover, it will provide a list of changes between both. Below you can find a small example:

```json
{
    "target": "{'path': [link] /var/lock, 'owner': [name]: daemon [uid]: 1, 'group': [name]: _ssh, [gid]: 106, 'mode': u: --- g: r-- o: -w-}\n",
    "actual": "{'path': [directory] /var/lock, 'owner': [name]: daemon [uid]: 1, 'group': [name]: _ssh, [gid]: 106, 'mode': u: --- g: r-- o: -w-}\n",
    "changes": {
        "values_changed": {
            "root['path']._PathStateValue__state.name": {
                "new_value": "DIRECTORY",
                "old_value": "SYMLINK"
            },
            "root['path']._PathStateValue__state.value": {
                "new_value": "directory",
                "old_value": "link"
            },
            "root['path'].state.name": {
                "new_value": "DIRECTORY",
                "old_value": "SYMLINK"
            },
            "root['path'].state.value": {
                "new_value": "directory",
                "old_value": "link"
            }
        }
    }
}
```

The actual representation of both states will depend on the wrapper that was used and how the wrappers state gets serialized by TRIaC.

#### TRIaC

The triac file is a base64 encoded binary file that holds all the wrappers and states that where needed to get to this error. Therefore, this file can be used to replay and therefore reproduce this error with TRIaC.

> [!IMPORTANT]  
>  The replay functionality has not been implemented yet.