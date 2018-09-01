# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import os
import sys
import re
# Third-Party Libraries
# N/A
# Custom Libraries
import em_constants

lib_name = 'lib'

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(
    path) or em_constants.APP_NAME in path]

# Add lib folder
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), lib_name]))

sys.path = new_paths
