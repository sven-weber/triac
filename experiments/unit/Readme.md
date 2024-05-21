## Unit testing


TODO: Update

This experiment tests the generability of TRIaC by running a more complex setup using the [community.postgresql.postgresql_db](https://docs.ansible.com/ansible/latest/collections/community/general/postgresql_db_module.html) module. The experiment was run for 200 round a 10 wrappers each. Therefore, there are 2000 wrapper executions in total.

## Repeat the experiment

The repeat the experiment, first you need to manually disable all but the ```PostgresDB``` wrapper. For this, navigate to the [/triac/wrappers](/triac/wrappers) folder. For each of the wrappers, **that is not postgres_db.py**, change the ```enabled``` function to return ```False```like so:

```python
@staticmethod
def enabled() -> bool:
    return False
```

Afterward, execute the following command:

```console
python3 -m triac --unit ANSIBLE --continue-on-error --keep-base-images --rounds 100 --wrappers-per-round 10
```

This will execute the experiment. We expect this to take rouhly 3 hours.

## Results

