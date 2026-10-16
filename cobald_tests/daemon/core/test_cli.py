import time
import sys
import subprocess
from tempfile import NamedTemporaryFile


def test_daemon_cli():
    with NamedTemporaryFile(suffix=".yaml") as config:
        with open(config.name, "w") as write_stream:
            write_stream.write("""
                pipeline:
                    - !LinearController
                        low_utilisation: 0.9
                        high_allocation: 1.1
                    - __type__: 'cobald_tests.mock.pool.MockPool'
                """)
        start_time = time.monotonic()
        subprocess.check_call(
            [sys.executable, "-m", "cobald.daemon", config.name, "--timeout", "0.5"],
            timeout=10.0,  # GH Action may run the process very slowly
        )
        duration = time.monotonic() - start_time
        assert duration >= 0.5, "daemon ran shorter than expected"
