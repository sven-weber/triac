## TRIaC: A generaTion-based fuzzing framework for Resilience in Infrastructure as Code

This repository contains the supplementary material for TRiAC, a tool for generation-based fuzzing that enables unit and differential testing of IaC tools. TRIaC achieves this through the use of Docker and so-called Wrappers that enable the testing of specific modules. As of now, the tool implements fuzzing for the [Ansible](https://www.ansible.com/) [builtin.file](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/file_module.html) module. Further modules and support for [pyinfra](https://pyinfra.com/) will be added in the near future.

TODO: IMAGE!

This readme provides instructions on how to use TRIaC to perform fuzzing. Instructions on how to extend the tool with new capabilities to cover more tools or modules can be found in the [triac/wrappers subfolder](/triac/wrappers/Readme.md).

> [!WARNING]  
> This tool is still under active development

# How to run TRIaC

To run TRIaC on your machine, there are two prerequisite that need to be fulfilled.

### 1. Prerequisite: Docker 

First, a recent installation of [Docker](https://www.docker.com/#build) is required. You can find instructions on how to install Docker [here](https://www.docker.com/#build). In order to communicate with docker, TRIaC requires that connection information for the Docker API are provided via the following environment variables. This should be the case by default for every Docker installation. If the connection should not work, you will find corresponding error messages when executing TRIaC.

| Variable          | description                                                                                   |
|-------------------|-----------------------------------------------------------------------------------------------|
| DOCKER_HOST       | The URL to the Docker host. For example unix:///var/run/docker.sock or  tcp://127.0.0.1:1234. |
| DOCKER_TLS_VERIFY | Whether to verify the host against a CA certificate                                           |
| DOCKER_CERT_PATH  | A path to a directory containing TLS certificates to use when connecting to the Docker host.  |

You can find further information in the [here](https://docker-py.readthedocs.io/en/stable/client.html#docker.client.from_env).

### 2. Prerequisite: Python & packages

To run TRIaC you need to have python 3 installed. Once the install is finished, you can install all of TRIaCs dependencies as follows:

```console
pip install -r requirements/prod.txt
```

If you also want to extend TRIaC we recommend installing the development dependencies as follows instead:

```console
pip install -r requirements/dev.txt
```



# Generated content