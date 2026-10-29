"""Canonical offline verification: product, grader calibration and original components."""
import json
from pathlib import Path
import socket
import sys
import unittest
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def forbidden(*args,**kwargs):raise RuntimeError('Network disabled by offline verification')


def main():
    socket.create_connection=forbidden;socket.socket.connect=forbidden;urllib.request.urlopen=forbidden
    loader=unittest.TestLoader();suite=loader.discover(str(ROOT/'tests'))
    originals=ROOT/'actual-source'
    if not originals.exists():originals=ROOT/'actual-source-candidate'
    suite.addTests(unittest.TestLoader().discover(str(originals/'tests')))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'network':'blocked','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                      'model_calls':0,'product_improvements':'not_authorized; not_performed'}))
    return 0 if result.wasSuccessful()else 1


if __name__=='__main__':raise SystemExit(main())
