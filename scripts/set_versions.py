import os
import re
import sys

version = sys.argv[1]
base_version = ".".join(version.split(".")[:2])
full_version = version + ".0" if re.match(r"^\d+\.\d+$", version) else version

with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write(f"BLENDER_BASE_VERSION={base_version}\n")
    f.write(f"FULL_VERSION={full_version}\n")
