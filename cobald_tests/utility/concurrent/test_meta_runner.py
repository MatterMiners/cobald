import threading
import pytest

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

    def test_abort_coroutine(self):
        async def abort():
            raise TerminateRunner

        for flavour in (trio,):
            runner = MetaRunner()
            runner.register_coroutine(coroutine=abort, flavour=flavour)
            with pytest.raises(TerminateRunner):
                runner.run()

