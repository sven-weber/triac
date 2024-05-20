## TRIaC: A generaTion-based fuzzing framework for Resilience in Infrastructure as Code

This repository contains the supplementary material for TRiAC, a tool for generation-based fuzzing that enables unit and differential testing of IaC tools. TRIaC achieves this through the use of Docker and so-called Wrappers that enable the testing of specific modules. TRIaC has been developed by [Luca Tagliavini](https://github.com/lucat1) and [Sven Weber](https://github.com/sven-weber) as part of a course on [Automated Software Testing](https://www.vorlesungen.ethz.ch/Vorlesungsverzeichnis/lerneinheit.view?semkez=2024S&lerneinheitId=177483&lang=en) held by [Prof. Dr. Zhendong Su](https://people.inf.ethz.ch/suz/) at [ETH Zurich](https://inf.ethz.ch/).


As of now, TRIaC implements fuzzing for the following [Ansible](https://www.ansible.com/) modules:

- [builtin.file](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/file_module.html)
- [community.postgresql.postgresql_db](https://docs.ansible.com/ansible/latest/collections/community/general/postgresql_db_module.html)
- [ansible.builtin.systemd_service](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/systemd_service_module.html)

Further TRIaC supports the following [pyinfra](https://pyinfra.com/) operations:

- [Systemd](https://docs.pyinfra.com/en/2.x/operations/systemd.html)

![Image](/img/example.png "Screenshot of a TRIaC run")

This readme provides instructions on how to use TRIaC to perform fuzzing. Instructions on how to extend the tool with new capabilities to cover more tools or modules can be found in the [triac/wrappers subfolder](/triac/wrappers/Readme.md). Moreover, the experimental results, raw data, and instructions on how to replicate the experiments can be found at [experiments](/experiments/Readme.d).

# How to run TRIaC

At the moment, the TRIaC has ben tested on macOS 14.4.1, Ubuntu 22.04, and Arch Linux 2024.05.01. However, it should also run on Windows with Docker Desktop, altough this has not been verified explicitly.

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

To run TRIaC you need to have [Python 3](https://www.python.org/downloads/) installed. Once the install is finished, you can install all of TRIaCs dependencies as follows:

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
python3 -m triac
```

However, to invoke TRIaC at least one of the following parameters needs to be supplied:

- ```--differential ANSIBLE:PYINFRA```
    - Start a differential fuzzing round that tests ansible against pyinfra
- ```--unit ANSIBLE``` or ```--unit PYINFRA```
    - Start a unit test that is executed with either ansible or pyinfra
- ```--replay ./errors/replay-file.triac```
    - Replay a error that was discovered by triac by specifying a error file

Moreover, there are many options available to control the fuzzing run. You can get all options via:

```console
python3 -m triac --help
```

Which will print the following:

```console
Usage: python -m triac [OPTIONS]

  Start a TRIaC fuzzing or replay session

Options:
  -R, --rounds INTEGER RANGE      Number of rounds to perform  [default: 2;
                                  x>=1]
  -W, --wrappers-per-round INTEGER RANGE
                                  The maximum number of wrappers to try in
                                  each round before starting the next round
                                  [default: 10; x>=1]
  --log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                  The log level to use for the generated log
                                  file  [default: DEBUG]
  --ui-log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                  The log level to display in the TRIaC Ui
                                  [default: INFO]
  -B, --base-image [DEBIAN12|UBUNTU22|DEBIAN12_POSTGRES16]
                                  The base image to use. If not specified, one
                                  is chosen randomly each round
  -K, --keep-base-images          Whether the base images that where build
                                  during the execution should be kept. This
                                  will increase the speed of future
                                  executions.
  -C, --continue-on-error         Whether triac should automatically continue
                                  with the execution of the next round
                                  whenever a unexpected error is encountered.
  -S, --slow-mode                 Enables a slow mode. This means that triac
                                  pauses after each wrapper execution and
                                  waits for user input to continue. This can
                                  be very helpful for debugging or demos
  -U, --unit [ANSIBLE|PYINFRA]    Enables unit testing the specified tool.
                                  This option cannot be supplied while
                                  performing differential testing.
  -D, --differential [ANSIBLE:PYINFRA]
                                  Enables differential testing between two
                                  tools. The tools have to be specified using
                                  one of the provided format options.
  --replay FILE                   This enables a replay. In this mode, TRIaC
                                  DOES NOT FUZZ but replays a previously found
                                  error from the /errors folder. When this
                                  option is supplied, only the log levels and
                                  keep-base-images options will be taken into
                                  account.
  --help                          Show this message and exit.
```

For example, you can control the number of rounds and how many wrappers should be run per round. Moreover, you can specific a fixed base image or increase the log level if you need further details.

No matter which options you choose, TRIaC will generate a log file and error files for each run which can later be used to debug and reproduce any found errors. See the section [Monitoring runs and reproducing errors](#monitoring-runs-and-reproducing-errors) below for further details.

### Running TRIaC repeatedly or unsupervised

If you plan on running TRIaC more than once, we recommend using the ```--keep-base-images``` option as follows:

```console
python3 -m triac --keep-base-images
```

Without this option, TRIaC will build all used base images for each run and cleanup the images once the run is finished. While this does not leave behind data on your machine, building the images can take some time. Therefore, if you are playing around with TRIaC or developing your own wrapper it is recommended to disable the image cleanup after the run via this option.

Moreover, if you plan on running TRIaC for a long time without supervision, it might make sense to enable ```--continue-on-error```. By default, TRIaC will stop the execution once a unexpected error is discovered. For example, an IaC execution might fail. In these cases, TRIaC will wait for the user to press Enter before the execution continues. However, due to the unpredictable nature of fuzzing this might not be the desired behavoir for long running tasks. For example, a fuzzing round might delete files by accident that are indispensable for TRIaC to function. In these cases, the execution will halt with an error. Alternatively, you can let TRIaC continue without any user input by using this option as follows:

```
python3 -m triac --continue-on-error
```

## Monitoring runs and reproducing errors

By default, TRIaC generates the following two things for every run

### Log file

A log file is generated in the root of the repository with the name ```triac.log```. This file contains DEBUG output by default and enables you to go through the whole execution in your own pace. Note that the information in this log file is much more detailed than what is visible in the UI by default. For example, the ```triac.log```contains all the generated files for Ansible any pyinfra as well as any output that was produced by invoking one of the tools. However, you can change the persisted log level with the ```--log-level``` option as shown above. Moreover, you can also adjust the log level for the UI via ```--ui-log-level```.

### Error files

For every state mismatch between target and actual state that TRIaC finds, it will generate two error files. The files are located inside a ```error``` folder in the root of this repository and the file name is the timestamp when the error was found. It will generate one ```.json``` and one ```.triac``` file.

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

To replay an error, execute the following:

```console
python3 -m triac --replay ./errors/{FILENAME}.triac
```

with the name of the file that you want to replay. TRIaC will then enter a replay mode where each of the wrappers needed to get to the discovered error will be executed with the exact same target states as defined when the error was discovered originally. Moreover, the user has to acknowledge the execution before the next wrapper will be executed. In this state, the container(s) against which the wrapper was executed will still exist. Therefore, you as a user can investigate the reached state within the actual target system step-by-step. Once you acknowledge the execution of the next wrapper, the container(s) from the previous wrapper will be removed.