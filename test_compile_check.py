import sys
sys.path.insert(0, 'backend/tests/test_cases')
import py_compile
result = py_compile.compile('backend/tests/test_cases/test_tdd_report_aggregation.py', doraise=True)
print("Compilation OK" if result else "FAIL")
