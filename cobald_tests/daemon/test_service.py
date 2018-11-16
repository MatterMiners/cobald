import threading
import pytest
import time
import random
import trio
import asyncio

import logging
import pytest

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
        """Assert that no payloads may be scheduled before starting"""
        def payload():
            return

        runner = ServiceRunner()
        runner._meta_runner.register_payload(payload, flavour=threading)
        with pytest.raises(RuntimeError):
            runner.accept()

    def test_service(self):
        """Test running service classes automatically"""
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

    def test_execute(self):
        """Test running payloads synchronously"""
        default = random.random()

        def sub_pingpong(what=default):
            return what

        async def co_pingpong(what=default):
            return what

        runner = ServiceRunner(accept_delay=0.1)
        run_in_thread(runner.accept, name='test_execute')
        # do not pass in values - receive default
        assert runner.execute(sub_pingpong, flavour=threading) == default
        assert runner.execute(co_pingpong, flavour=trio) == default
        assert runner.execute(co_pingpong, flavour=asyncio) == default
        # pass in positional arguments
        assert runner.execute(sub_pingpong, 1, flavour=threading) == 1
        assert runner.execute(co_pingpong, 2, flavour=trio) == 2
        assert runner.execute(co_pingpong, 3, flavour=asyncio) == 3
        # pass in keyword arguments
        assert runner.execute(sub_pingpong, what=1, flavour=threading) == 1
        assert runner.execute(co_pingpong, what=2, flavour=trio) == 2
        assert runner.execute(co_pingpong, what=3, flavour=asyncio) == 3

    def test_adopt(self):
        """Test running payloads asynchronously"""
        default = random.random()
        reply_store = []

        def sub_pingpong(what=default):
            reply_store.append(what)

        async def co_pingpong(what=default):
            reply_store.append(what)

        runner = ServiceRunner(accept_delay=0.1)
        run_in_thread(runner.accept, name='test_execute')
        # do not pass in values - receive default
        assert runner.adopt(sub_pingpong, flavour=threading) is None
        assert runner.adopt(co_pingpong, flavour=trio) is None
        assert runner.adopt(co_pingpong, flavour=asyncio) is None
        # pass in positional arguments
        assert runner.adopt(sub_pingpong, 1, flavour=threading) is None
        assert runner.adopt(co_pingpong, 2, flavour=trio) is None
        assert runner.adopt(co_pingpong, 3, flavour=asyncio) is None
        # pass in keyword arguments
        assert runner.adopt(sub_pingpong, what=4, flavour=threading) is None
        assert runner.adopt(co_pingpong, what=5, flavour=trio) is None
        assert runner.adopt(co_pingpong, what=6, flavour=asyncio) is None
        for _ in range(10):
            time.sleep(0.05)
            if len(reply_store) == 9:
                assert reply_store.count(default) == 3
                assert set(reply_store) == {default} | set(range(1, 7))
                break
        else:
            assert len(reply_store) == 9
