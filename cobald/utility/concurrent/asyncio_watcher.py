import asyncio

from .base_runner import BaseRunner
from .thread_runner import CapturingThread


async def watch_runner(runner: BaseRunner):
    runner_thread = CapturingThread(target=runner.run)
    runner_thread.start()
    delay = 0.0
    while not runner_thread.join(timeout=0):
        await asyncio.sleep(delay)
        delay = min(delay + 0.1, 1.0)


class AsyncioMainWatcher(object):
    """
    Special ``asyncio`` event loop running in the main thread and watching runners

    .. seealso:: The `issue #8 <https://github.com/MaineKuehn/cobald/issues/8>`_ for details.
    """
    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.get_event_loop()
        asyncio.get_child_watcher().attach_loop(self.event_loop)

    def run(self, root_runner: BaseRunner):
        self.event_loop.run_until_complete(watch_runner(root_runner))
