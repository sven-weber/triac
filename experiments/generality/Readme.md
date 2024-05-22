## Generability of triac

This experiment tests the generality of TRIaC by running a more complex setup using the [community.postgresql.postgresql_db](https://docs.ansible.com/ansible/latest/collections/community/general/postgresql_db_module.html) module. The experiment was run for 80 round a 10 wrappers each. Therefore, there are 800 wrapper executions in total.

## Repeat the experiment

To repeat the experiment, first you need to manually disable all but the ```PostgresDB``` wrapper. For this, navigate to the [/triac/wrappers](/triac/wrappers) folder. For each of the wrappers, **that is not postgres_db.py**, change the ```enabled``` function to return ```False``` like so:

```python
@staticmethod
def enabled() -> bool:
    return False
```

Afterward, execute the following command:

```console
python3 -m triac --unit ANSIBLE --continue-on-error --keep-base-images --rounds 80 --wrappers-per-round 10 -B DEBIAN12_POSTGRES16
```

This will execute the experiment. We expect this to take roughly 4 and a half hours.

## Results

Our execution took 4 hours, 23 minutes and 18 seconds. Below is a screenshot of the finished execution:

![Image](/experiments/generality/screenshot.png "Screenshot of the TRIaC experiment for generality")

Our execution did not uncover any state mismatches from the ansible execution and the expected state. You can find the whole execution log, including all details in the ```triac.log``` file in this folder.