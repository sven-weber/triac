## Unit testing

This experiment tests the unit testing capabilities of TRIaC by running both Ansible using the [builtin.file](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/file_module.html) module. The experiment was run for 100 round a 10 wrappers each for a total of 1000 executed wrappers.

## Repeat the experiment

To repeat the experiment, first you need to manually disable all but the ```File``` wrapper. For this, navigate to the [/triac/wrappers](/triac/wrappers) folder. For each of the wrappers, **that is not file.py**, change the ```enabled``` function to return ```False```like so:

```python
@staticmethod
def enabled() -> bool:
    return False
```

Afterward, execute the following command:

```console
python3 -m triac --unit ANSIBLE --continue-on-error --keep-base-images --rounds 100 --wrappers-per-round 10
```

This will execute the experiment. We expect this to take roughly 1 hours and 45 minutes.

## Results

Our execution took 1 hour, 28 minutes and 23 seconds. Below is a screenshot of the finished execution:

![Image](/experiments/unit/screenshot.png "Screenshot of the TRIaC experiment for unit testing")

You can find the whole execution log, including all details in the ```triac.log``` file in this folder.

In total, we uncovered 6 errors. All of those errors where due to errors in our wrapper implementation that have been fixed since then. You can see our report for details on the kind of errors we encountered.