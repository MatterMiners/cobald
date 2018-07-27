import threading
import pytest
import time

import logging

from cobald.daemon.service import ServiceRunner, service


logging.getLogger().level = 10


class TerminateRunner(Exception):
    pass


def run_in_thread(payload, name, daemon=True):
    thread = threading.Thread(target=payload, name=name, daemon=daemon)
    thread.start()
    time.sleep(0.0)


class TestServiceRunner(object):
    def test_no_tainting(self):
        """Assert that no payloads may be scheduler before starting"""
        def payload():
            return

        runner = ServiceRunner()
        runner._meta_runner.register_payload(payload, flavour=threading)
        with pytest.raises(RuntimeError):
            runner.accept()

    def test_service(self):
        runner = ServiceRunner(accept_delay=0.1)
        replies = []

        @service(flavour=threading)
        class Service(object):
            def __init__(self):
                self.done = threading.Event()
                self.done.clear()

            def run(self):
                replies.append(1)
                self.done.set()

        a = Service()
        run_in_thread(runner.accept, name='test_service')
        assert a.done.wait(timeout=5), 'service thread completed'
        assert len(replies) == 1, 'pre-registered service ran'
        b = Service()
        assert b.done.wait(timeout=5), 'service thread completed'
        assert len(replies) == 2, 'post-registered service ran'
        runner.shutdown()
