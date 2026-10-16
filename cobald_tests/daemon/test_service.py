from types import ModuleType
import threading
import time
import random
import trio
import asyncio
import logging
import signal
import os

import pytest

from cobald.daemon.runners.service import ServiceRunner, service

logging.getLogger().level = 10


def sync_raise(what: BaseException):
    logging.info(f"raising {what}")
    raise what


async def async_raise(what: BaseException):
    sync_raise(what)


def sync_raise_signal(what: int, sleep):
    if sleep is not None:
        sleep(0.01)
    logging.info(f"signal {what}")
    os.kill(os.getpid(), what)


async def async_raise_signal(what: int, sleep):
    await sleep(0.01)
    sync_raise_signal(what, None)


class TestServiceRunner(object):
    def test_unique_runner(self):
        """Assert that no two runners may run services"""

        async def run_services_twice():
            return await asyncio.gather(
                ServiceRunner().run_services(), ServiceRunner().run_services()
            )

        with pytest.raises(RuntimeError):
            asyncio.run(run_services_twice())

    def test_service_execution(self):
        """Test that service instances are run automatically"""
        replies = 0

        @service(flavour=asyncio)
        class Service(object):
            def __init__(self):
                self.done = asyncio.Event()
                self.done.clear()

            async def run(self):
                nonlocal replies
                replies += 1
                self.done.set()

        async def run_services_automatically():
            pre_created = Service()
            runner_task = asyncio.create_task(ServiceRunner().run_services())
            async with asyncio.timeout(1):
                await pre_created.done.wait()
                assert replies == 1, "pre-created service did not run"
                late_created = Service()
                await late_created.done.wait()
                assert replies == 2, "late-created service did not run"
            runner_task.cancel()

        asyncio.run(run_services_automatically())

    @pytest.mark.parametrize("flavour", [threading, trio])
    def test_service_execution_foreign(self, flavour: ModuleType):
        """Test that service instances are run automatically"""
        replies = 0

        @service(flavour=flavour)
        class Service(object):
            def __init__(self):
                self.loop = asyncio.get_running_loop()
                self.done = asyncio.Event()
                self.done.clear()

            def _run(self):
                nonlocal replies
                replies += 1
                self.loop.call_soon_threadsafe(self.done.set)

            if flavour is trio:

                async def run(self):
                    self._run()

            else:
                run = _run

        async def run_services_automatically():
            pre_created = Service()
            runner_task = asyncio.create_task(ServiceRunner().run_services())
            async with asyncio.timeout(1):
                await pre_created.done.wait()
                assert replies == 1, "pre-created service did not run"
                late_created = Service()
                await late_created.done.wait()
                assert replies == 2, "late-created service did not run"
            runner_task.cancel()

        asyncio.run(run_services_automatically())

    # legacy meta runner framework
    def test_execute(self):
        """Test running payloads synchronously"""
        default = random.random()

        def sub_pingpong(what=default):
            return what

        async def co_pingpong(what=default):
            return what

        async def execute_payloads():
            runner = ServiceRunner()
            runner_task = asyncio.create_task(runner.run_services())
            await asyncio.sleep(0)
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
            runner_task.cancel()

        asyncio.run(execute_payloads())

    def test_adopt(self):
        """Test running payloads asynchronously"""
        default = random.random()
        reply_store = []

        def sub_pingpong(what=default):
            reply_store.append(what)

        async def co_pingpong(what=default):
            reply_store.append(what)

        async def adopt_payloads():
            runner = ServiceRunner()
            runner_task = asyncio.create_task(runner.run_services())
            await asyncio.sleep(0)
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
                await asyncio.sleep(0.05)
                if len(reply_store) == 9:
                    assert reply_store.count(default) == 3
                    assert set(reply_store) == {default, *range(1, 7)}
                    break
            else:
                assert False, "tasks were not adopeted/run in the background"
            runner_task.cancel()

        asyncio.run(adopt_payloads())

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
        runner = ServiceRunner()
        runner.adopt(do_sleep, 5, flavour=flavour)
        runner.adopt(do_raise, LookupError, flavour=flavour)
        with pytest.raises(ExceptionGroup):
            asyncio.run(runner.run_services())

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
        runner = ServiceRunner()
        runner.adopt(do_sleep, 5, flavour=flavour)
        # signal.SIGINT == KeyboardInterrupt
        runner.adopt(do_raise, signal.SIGINT, do_sleep, flavour=flavour)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(runner.run_services())
