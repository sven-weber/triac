import base64
import os
import pickle
from glob import glob
from os.path import join
from sys import argv

from triac.lib.encoding import encode, decode

# Expected arguments:
#  1. The path to the module definitions of TrIAC
#  2. pickle dump of the object as a base64 utf-8 encoded string
#  3. The name of the method to call
#
# Result: pickle encoded base64 string of the method result

if len(argv) != 4:
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
    import_path = module.replace("/", ".").replace(".py", "")
    mod = __import__(import_path, fromlist=[None])

# Read in the object
obj = decode(argv[2])

# Call the method
method = getattr(obj, argv[3])
res = method()

# Pickle the result
encoded_obj = encode(res)

# Print the result
print(encoded_obj)

exit(0)
