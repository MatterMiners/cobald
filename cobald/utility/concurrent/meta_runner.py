import logging
import threading
import trio


from .trio_runner import TrioRunner
from .asyncio_runner import AsyncioRunner
from .thread_runner import ThreadRunner


from ...utility.debug import NameRepr


class MetaRunner(object):
    """
    Unified interface to schedule subroutines and coroutines for concurrent execution
    """
    def __init__(self):
        self._logger = logging.getLogger('cobald.runtime.runner.meta')
        self.runners = {
            runner.flavour: runner() for runner in (TrioRunner, AsyncioRunner, ThreadRunner)
        }

    def register_coroutine(self, *coroutines, flavour=trio):
        """Queue one or more coroutine for execution after its runner is started"""
        for coroutine in coroutines:
            self._logger.debug('registering coroutine %s (%s)', NameRepr(coroutine), NameRepr(flavour))
            self.runners[flavour].register_payload(coroutine)

    def register_subroutine(self, *subroutines, flavour=threading):
        """Queue one or more subroutine for execution after its runner is started"""
        for subroutine in subroutines:
            self._logger.debug('registering subroutine %s (%s)', NameRepr(subroutine), NameRepr(flavour))
            self.runners[flavour].register_payload(subroutine)

    def run(self):
        """Run all runners until completion"""
        self._logger.info('starting all runners')
        try:
            thread_runner = self.runners[threading]
            for runner in self.runners.values():
                if runner is not thread_runner:
                    thread_runner.register_subroutine(runner.run)
            thread_runner.run()
        except Exception as err:
            self._logger.error('runner terminated: %s', err)
            raise
        finally:
            for runner in self.runners.values():
                runner.stop()
            self._logger.info('stopped all runners')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    import time
    import asyncio
    runner = MetaRunner()

    async def trio_sleeper():
        for i in range(3):
            print('trio\t', i)
            await trio.sleep(0.1)
    runner.register_coroutine(trio_sleeper)

    async def asyncio_sleeper():
        for i in range(3):
            print('asyncio\t', i)
            await asyncio.sleep(0.1)
    runner.register_coroutine(asyncio_sleeper, flavour=asyncio)

    def thread_sleeper():
        for i in range(3):
            print('thread\t', i)
            time.sleep(0.1)
    runner.register_subroutine(thread_sleeper, flavour=threading)

    async def teardown():
        await trio.sleep(5)
        raise SystemExit('Abort from trio runner')
    runner.register_coroutine(teardown)

    runner.run()
