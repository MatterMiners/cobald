import threading
import time
import random
import trio
import asyncio
import contextlib
import logging
import signal
import os
import gc

import pytest

from cobald.daemon.runners.service import ServiceRunner, service


logging.getLogger().level = 10


class TerminateRunner(Exception):
    pass


@contextlib.contextmanager
def accept(payload: ServiceRunner, name):
    gc.collect()
    thread = threading.Thread(target=payload.accept, name=name, daemon=True)
    thread.start()
    if not payload.running.wait(1):
        payload.shutdown()
        raise RuntimeError(
            f"{payload} failed to start (thread {thread}, all {threading.enumerate()})"
        )
    try:
        yield
    finally:
        payload.shutdown()
        thread.join(timeout=1)


def sync_raise(what):
    logging.info(f"raising {what}")
    raise what


async def async_raise(what):
    sync_raise(what)


def sync_raise_signal(what, sleep):
    if sleep is not None:
        sleep(0.01)
    logging.info(f"signal {what}")
    os.kill(os.getpid(), what)


async def async_raise_signal(what, sleep):
    await sleep(0.01)
    sync_raise_signal(what, None)


class TestServiceRunner(object):
    def test_unique_reaper(self):
        """Assert that no two runners may fetch services"""
        with accept(ServiceRunner(accept_delay=0.1), name="outer"):
            with pytest.raises(RuntimeError):
                ServiceRunner(accept_delay=0.1).accept()

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
        with accept(runner, name="test_service"):
            assert a.done.wait(timeout=5), "service thread completed"
            assert len(replies) == 1, "pre-registered service ran"
            b = Service()
            assert b.done.wait(timeout=5), "service thread completed"
            assert len(replies) == 2, "post-registered service ran"

    def test_execute(self):
        """Test running payloads synchronously"""
        default = random.random()

        def sub_pingpong(what=default):
            return what

        async def co_pingpong(what=default):
            return what

        runner = ServiceRunner(accept_delay=0.1)
        with accept(runner, name="test_execute"):
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
        with accept(runner, name="test_adopt"):
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

    @pytest.mark.parametrize(
        "flavour, do_sleep, do_raise",
        (
            (asyncio, asyncio.sleep, async_raise),
            (trio, trio.sleep, async_raise),
            (threading, time.sleep, sync_raise),
        ),
    )
    def test_error_reporting(self, flavour, do_sleep, do_raise):
        """Test that fatal errors do not pass silently"""
        # errors should fail the entire runtime
        runner = ServiceRunner(accept_delay=0.1)
        runner.adopt(do_sleep, 5, flavour=flavour)
        runner.adopt(do_raise, LookupError, flavour=flavour)
        with pytest.raises(RuntimeError):
            runner.accept()

    @pytest.mark.parametrize(
        "flavour, do_sleep, do_raise",
        (
            (asyncio, asyncio.sleep, async_raise_signal),
            (trio, trio.sleep, async_raise_signal),
            (threading, time.sleep, sync_raise_signal),
        ),
    )
    def test_interrupt(self, flavour, do_sleep, do_raise):
        """Test that KeyboardInterrupt/^C is graceful shutdown"""
        runner = ServiceRunner(accept_delay=0.1)
        runner.adopt(do_sleep, 5, flavour=flavour)
        # signal.SIGINT == KeyboardInterrupt
        runner.adopt(do_raise, signal.SIGINT, do_sleep, flavour=flavour)
        runner.accept()
