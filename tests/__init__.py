"""Tests aislados: el cwd se mueve a un directorio temporal antes de importar
app.core para no tocar la base de datos real del proyecto."""

import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="sdimport_tests_")
os.chdir(_TMP)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
