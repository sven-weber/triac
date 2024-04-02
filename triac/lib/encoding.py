from base64 import b64encode, b64decode
from pickle import dumps, loads

def encode(obj: object) -> str:
    enc = dumps(obj)
    b64enc = b64encode(enc).decode("utf-8")
    return b64enc

def decode(b64enc: str) -> object:
    enc = b64decode(b64enc)
    obj = loads(enc)
    return obj
