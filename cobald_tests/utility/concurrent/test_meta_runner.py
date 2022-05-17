import threading
import pytest
import time
import asyncio
import contextlib
import gc

import trio

from cobald.daemon.runners.base_runner import OrphanedReturn
from cobald.daemon.runners.meta_runner import MetaRunner


class TerminateRunner(Exception):
    pass


@contextlib.contextmanager
def threaded_run(name):
    gc.collect()
    runner = MetaRunner()
    thread = threading.Thread(target=runner.run, name=name, daemon=True)
    thread.start()
    if not runner.running.wait(1):
        runner.stop()
        raise RuntimeError(
            f"{runner} failed to start (thread {thread}, all {threading.enumerate()})"
        )
    try:
        yield runner
    finally:
        runner.stop()
        thread.join(timeout=1)


class TestMetaRunner(object):
    @pytest.mark.parametrize("flavour", (threading,))
    def test_run_subroutine(self, flavour):
        """Test executing a subroutine"""

        def with_return():
            return "expected return value"

        def with_raise():
            raise KeyError("expected exception")

        with threaded_run("test_run_subroutine") as runner:
            result = runner.run_payload(with_return, flavour=flavour)
            assert result == with_return()
            with pytest.raises(KeyError):
                runner.run_payload(with_raise, flavour=flavour)

    @pytest.mark.parametrize("flavour", (asyncio, trio))
    def test_run_coroutine(self, flavour):
        """Test executing a coroutine"""

        async def with_return():
            return "expected return value"

        async def with_raise():
            raise KeyError("expected exception")

        with threaded_run("test_run_coroutine") as runner:
            result = runner.run_payload(with_return, flavour=flavour)
            assert result == trio.run(with_return)
            with pytest.raises(KeyError):
                runner.run_payload(with_raise, flavour=flavour)

    @pytest.mark.parametrize("flavour", (threading,))
    def test_return_subroutine(self, flavour):
        """Test that returning from subroutines aborts runners"""

        def with_return():
            return "unhandled return value"

        runner = MetaRunner()
        runner.register_payload(with_return, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, OrphanedReturn)

    @pytest.mark.parametrize("flavour", (asyncio, trio))
    def test_return_coroutine(self, flavour):
        """Test that returning from subroutines aborts runners"""

        async def with_return():
            return "unhandled return value"

        runner = MetaRunner()
        runner.register_payload(with_return, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, OrphanedReturn)

    @pytest.mark.parametrize("flavour", (threading,))
    def test_abort_subroutine(self, flavour):
        """Test that failing subroutines abort runners"""

        def abort():
            raise TerminateRunner

        runner = MetaRunner()
        runner.register_payload(abort, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, TerminateRunner)

        def noop():
            return

        def loop():
            while True:
                time.sleep(0)

        runner = MetaRunner()
        runner.register_payload(noop, loop, flavour=flavour)
        runner.register_payload(abort, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, TerminateRunner)

    @pytest.mark.parametrize("flavour", (asyncio, trio))
    def test_abort_coroutine(self, flavour):
        """Test that failing coroutines abort runners"""

        async def abort():
            raise TerminateRunner

        runner = MetaRunner()
        runner.register_payload(abort, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, TerminateRunner)

        async def noop():
            return

        async def loop():
            while True:
                await flavour.sleep(0)

        runner = MetaRunner()
        runner.register_payload(noop, loop, flavour=flavour)
        runner.register_payload(abort, flavour=flavour)
        with pytest.raises(RuntimeError) as exc:
            runner.run()
        assert isinstance(exc.value.__cause__, TerminateRunner)
