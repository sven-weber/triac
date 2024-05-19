import base64
import io
import os
import pickle
import re
from contextlib import redirect_stderr, redirect_stdout
from glob import glob
from os.path import join
from sys import argv

from triac.lib.encoding import decode, encode

# Expected arguments:
#  1.    The path to the module definitions of TrIAC
#  2.    pickle dump of the object as a base64 utf-8 encoded string
#  3.    The name of the method to call
#  4..n. A list of optional arguments to use
#
# Result: pickle encoded base64 string of the method result

if len(argv) < 4:
    print(f"Got invalid arguments! Gotten: {argv}")
    exit(1)

#
# IMPORTANT: This script should only contain one print statement
#            at the end. Otherwise the client is not able to parse
#            the results
#

#
# Import all python modules from TRIaC directory
#
import_path = argv[1]
modules = []
for root, dirs, files in os.walk(import_path):
    modules.extend([join(root, file) for file in files if file.endswith(".py")])

modules = list(filter(lambda f: "__init__" not in f and "__main__" not in f, modules))
last_folder = os.path.basename(os.path.normpath(import_path))
base_path = import_path[0 : len(import_path) - len(last_folder)]
modules = list(map(lambda f: f.replace(base_path, ""), modules))

for module in modules:
    # We only want to replace the .py at the end
    # Otherwise, we will screw up files like lib.pysmth.py
    import_path = re.sub(".py$", "", module.replace("/", "."))
    mod = __import__(import_path, fromlist=[None])

# Read in the object
obj = decode(argv[2])
arguments = [decode(arg) for arg in argv[4:]]

# Call the method with captured stdout and stderr
try:
    o = io.StringIO()
    e = io.StringIO()
    with redirect_stdout(o):
        with redirect_stderr(e):
            method = getattr(obj, argv[3])
            if len(arguments) > 0:
                res = method(*arguments)
            else:
                res = method()
except Exception as e:
    print("Method failed with exception:")
    print(e)
    print("Following content was printed during execution.")
    print("stdout:")
    print(o.getvalue())
    print("stderr:")
    print(e.getvalue())
    exit(1)

# Get the output and wrap it to send it back
result = {}
result["method_result"] = res
result["std_out"] = o.getvalue()
result["std_err"] = e.getvalue()

# Pickle the result
encoded_obj = encode(result)

# Print the result
print(encoded_obj)

exit(0)
