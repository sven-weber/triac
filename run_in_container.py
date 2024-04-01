from sys import argv

mod = __import__(argv[1], fromlist=[None])
cls = getattr(mod, argv[2])

state = cls.verify()
print(state)
