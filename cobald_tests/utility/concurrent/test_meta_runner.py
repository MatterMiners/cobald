import threading
import pytest
import time

import trio

from cobald.utility.concurrent.meta_runner import MetaRunner


class TerminateRunner(Exception):
    pass


class TestMetaRunner(object):
    def test_abort_subroutine(self):
        def abort():
            raise TerminateRunner

        for flavour in (threading,):
            runner = MetaRunner()
            runner.register_subroutine(subroutine=abort, flavour=flavour)
            with pytest.raises(TerminateRunner):
                runner.run()

            def noop():
                while True:
                    time.sleep(0)
            runner = MetaRunner()
            runner.register_subroutine(subroutine=noop, flavour=flavour)
            runner.register_subroutine(subroutine=abort, flavour=flavour)
            with pytest.raises(TerminateRunner):
                runner.run()

    def test_abort_coroutine(self):
        async def abort():
            raise TerminateRunner

        for flavour in (trio,):
            runner = MetaRunner()
            runner.register_coroutine(coroutine=abort, flavour=flavour)
            with pytest.raises(TerminateRunner):
                runner.run()

            async def noop():
                while True:
                    await flavour.sleep(0)
            runner = MetaRunner()
            runner.register_coroutine(coroutine=noop, flavour=flavour)
            runner.register_coroutine(coroutine=abort, flavour=flavour)
            with pytest.raises(TerminateRunner):
                runner.run()
