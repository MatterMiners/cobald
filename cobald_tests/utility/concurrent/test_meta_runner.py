import threading
import pytest
import time
import asyncio

import trio

from cobald.utility.concurrent.base_runner import OrphanedReturn
from cobald.utility.concurrent.meta_runner import MetaRunner


class TerminateRunner(Exception):
    pass


def run_in_thread(payload, name, daemon=True):
    thread = threading.Thread(target=payload, name=name, daemon=daemon)
    thread.start()
    time.sleep(0.0)


class TestMetaRunner(object):
    def test_bool_payloads(self):
        def subroutine():
            time.sleep(0.5)

        async def a_coroutine():
            await asyncio.sleep(0.5)

        async def t_coroutine():
            await trio.sleep(0.5)

        for flavour, payload in ((threading, subroutine), (asyncio, a_coroutine), (trio, t_coroutine)):
            runner = MetaRunner()
            assert not bool(runner)
            runner.register_payload(payload, flavour=flavour)
            assert bool(runner)
            run_in_thread(runner.run, name='test_bool_payloads %s' % flavour)
            assert bool(runner)
            runner.stop()

    def test_run_subroutine(self):
        """Test executing a subroutine"""
        def with_return():
            return 'expected return value'

        def with_raise():
            raise KeyError('expected exception')

        for flavour in (threading,):
            runner = MetaRunner()
            result = runner.run_payload(with_return, flavour=flavour)
            assert result == with_return()
            with pytest.raises(KeyError):
                runner.run_payload(with_raise, flavour=flavour)

    def test_run_coroutine(self):
        """Test executing a subroutine"""
        async def with_return():
            return 'expected return value'

        async def with_raise():
            raise KeyError('expected exception')

        for flavour in (trio, asyncio):
            runner = MetaRunner()
            run_in_thread(runner.run, name='test_run_coroutine %s' % flavour)
            result = runner.run_payload(with_return, flavour=flavour)
            # TODO: can we actually get the value from with_return?
            assert result == 'expected return value'
            with pytest.raises(KeyError):
                runner.run_payload(with_raise, flavour=flavour)
            runner.stop()

    def test_return_subroutine(self):
        """Test that returning from subroutines aborts runners"""
        def with_return():
            return 'unhandled return value'

        for flavour in (threading,):
            runner = MetaRunner()
            runner.register_payload(with_return, flavour=flavour)
            with pytest.raises(RuntimeError) as exc:
                runner.run()
            assert isinstance(exc.value.__cause__, OrphanedReturn)

    def test_return_coroutine(self):
        """Test that returning from subroutines aborts runners"""
        async def with_return():
            return 'unhandled return value'

        for flavour in (asyncio, trio):
            runner = MetaRunner()
            runner.register_payload(with_return, flavour=flavour)
            with pytest.raises(RuntimeError) as exc:
                runner.run()
            assert isinstance(exc.value.__cause__, OrphanedReturn)

    def test_abort_subroutine(self):
        """Test that failing subroutines abort runners"""
        def abort():
            raise TerminateRunner

        for flavour in (threading,):
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

    def test_abort_coroutine(self):
        """Test that failing coroutines abort runners"""
        async def abort():
            raise TerminateRunner

        for flavour in (asyncio, trio):
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
