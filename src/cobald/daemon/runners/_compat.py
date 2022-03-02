import sys
import asyncio
import inspect


if sys.version_info >= (3, 7):
    asyncio_run = asyncio.run
else:
    # almost literal backport of asyncio.run
    def asyncio_run(main, *, debug=None):
        assert inspect.iscoroutine(main)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            if debug is not None:
                loop.set_debug(debug)
            return loop.run_until_complete(main)
        finally:
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

    def _cancel_all_tasks(loop):
        to_cancel = asyncio.Task.all_tasks(loop)
        if not to_cancel:
            return
        for task in to_cancel:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))
        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler(
                    {
                        "message": "unhandled exception during asyncio.run() shutdown",
                        "exception": task.exception(),
                        "task": task,
                    }
                )


if sys.version_info >= (3, 7):
    asyncio_current_task = asyncio.current_task
else:

    def asyncio_current_task() -> asyncio.Task:
        return asyncio.Task.current_task()
