# TRIaC wrappers

The following guide gives a short instruction into writing your own TRIaC wrapper. You can find examples of wrappers in this folder.

A wrapper extends the TRIaC ```Wrapper``` class and needs to have at least the following methods:

```python
class File(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {
            "key": ValueType()
        }

    @staticmethod
    def supported_targets() -> List[Target]:
        return [Target.ANSIBLE]

    @staticmethod
    def enabled() -> bool:
        return True

    @staticmethod
    def transform(target: Target, state: State) -> str:
        
    @staticmethod
    def verify(exp: State) -> State:
```

The ```definition``` method should return the wrappers state definition. A definition is a dictionary that maps strings to a TRIaC ```BaseType```. This ```BaseType``` implements a ```generate``` function that produces valid instantiation of this type. This ```generate``` method will be executed within the target environment such that you can e.g. fetch a list of all valid files and return one of it. There are already existing types you can reuse or you can write your own types if required.

The ```supported_targets`` method should return a list of targets that are supported by this wrapper. For example, the wrapper above will only be executed with Ansible. If a wrapper should be used for differential testing it needs to support at least two targets.

The ```enabled``` method should return whether the wrapper is useable for TRIaC. For example, a wrapper implementation might not be finished. In these cases, you can disable the wrapper. This feature also allows the usage of specific wrappers by disabling all wappers that should not be used. 

The ```transform``` method should take a provided state and transform it into a string that can be used to invoke the provided IaC target. This method should support all targets that are returned by the ```supported_targets``` method.

The ```verify``` method will be executed inside the target container after the IaC tool has been invoked. The method should return a ```State``` object that represents the actual, reached state. It might be needed to know the target state for this operation, which is why it is supplied as a parameter to the method.

Lastly, a wrapper can optionally implement a ```can_execute``` method as follows:

```python
class File(Wrapper):
...
    @staticmethod
    def can_execute() -> bool:
        perform_dependency_check()
```

This method will be executed in the target environment before ```transform``` is called or the IaC tool is invoked to check if the environment is suitable for the wrapper. By default this method returns ```True```. You can use this method to check for any dependencies you might have for your wrapper (like a valid PostgreSQL installation). If the wrapper is not suitable, it will not be executed in this environment by TRIaC.