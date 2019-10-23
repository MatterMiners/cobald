import asyncio
import threading
import sys

from .base_runner import BaseRunner
from .thread_runner import CapturingThread


async def awaitable_runner(runner: BaseRunner):
    """Execute a runner without blocking the event loop"""
    runner_thread = CapturingThread(target=runner.run)
    runner_thread.start()
    delay = 0.0
    while not runner_thread.join(timeout=0):
        await asyncio.sleep(delay)
        delay = min(delay + 0.1, 1.0)


def asyncio_main_run(root_runner: BaseRunner):
    """
    Create an ``asyncio`` event loop running in the main thread and watching runners

    Using ``asyncio`` to handle subprocesses requires a specific loop type
    to run in the main thread.
    This function sets up and runs the correct loop in a portable way.
    In addition, it runs a single :py:class:`~.BaseRunner` until completion
    or failure.

    .. seealso:: The `issue #8 <https://github.com/MatterMiners/cobald/issues/8>`_
                 for details.
    """
    assert (
        threading.current_thread() == threading.main_thread()
    ), "only main thread can accept asyncio subprocesses"
    if sys.platform == "win32":
        event_loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(event_loop)
    else:
        event_loop = asyncio.get_event_loop()
        asyncio.get_child_watcher().attach_loop(event_loop)
    event_loop.run_until_complete(awaitable_runner(root_runner))
