# -*- coding: utf-8 -*-
"""Run through probe_python27 with the installed CE3X directory as argument."""

import json
import os
import sys

sys.frozen = 'console_exe'
sys.executable = os.path.join(os.getcwd(), os.environ['CE3X_PROBE_EXE'])
sys.path.insert(0, os.getcwd())

import __builtin__
__builtin__._ = lambda text: text
from Calculos.funcionesCalculo import getDiccionarioTemperaturasAguaRedACS

with open(os.environ['CE3X_PROBE_OUTPUT'], 'wb') as report:
    report.write(json.dumps(getDiccionarioTemperaturasAguaRedACS(), indent=2, sort_keys=True))
