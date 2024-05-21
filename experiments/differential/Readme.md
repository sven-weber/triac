## Differential testing

This experiment tests the differential testing capabilities of TRIaC by running both Ansible and pyinfra using the Ansible [ansible.builtin.systemd_service](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/systemd_service_module.html) module and the pyinfra [Systemd](https://docs.pyinfra.com/en/2.x/operations/systemd.html) operation. The experiment was run for 100 round a 10 wrappers each. Since each wrapper is executed twice in this setting this consitutes 2000 executions in total. 

## Repeat the experiment

The repeat the experiment, first you need to manually disable all but the ```Systemd``` wrapper. For this, navigate to the [/triac/wrappers](/triac/wrappers) folder. For each of the wrappers, **that is not systemd.py**, change the ```enabled``` function to return ```False```like so:

```python
@staticmethod
def enabled() -> bool:
    return False
```

Afterward, execute the following command:

```console
python3 -m triac --differential ANSIBLE:PYINFRA --continue-on-error --keep-base-images --rounds 100 --wrappers-per-round 10
```

This will execute the experiment. We expect this to take rouhly 3 hours.

## Results

Our execution took 3 hours, 1 minute and 22 seconds. Below is a screenshot of the finished execution:

![Image](/experiments/differential/screenshot.png "Screenshot of the TRIaC experiment for differential testing")

Our execution did not uncover any state mismatches between pyinfra, ansible, and the expected state. You can find the whole execution log, including all details in the ```triac.log``` file in this folder.