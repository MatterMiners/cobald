import asyncio
import contextlib
import logging
import sys
import textwrap

import pytest

from ..mock.pool import MockPool

from cobald.controller.streaming import StreamingController
from cobald.utility import InvariantError


def write_script(tmp_path, body):
    script = tmp_path / "script.py"
    script.write_text(textwrap.dedent(body))
    return str(script)


async def run_briefly(coro_factory, duration):
    """Run a coroutine as a task, cancel it after ``duration``, and await it"""
    task = asyncio.create_task(coro_factory())
    await asyncio.sleep(duration)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


class FakeProcess:
    """Stand-in for ``asyncio.subprocess.Process`` used to test cleanup/restart logic

    Yields ``lines`` on ``stdout``. If ``running`` is True (default), behaves as if
    the process is still alive afterwards, until ``terminate``/``kill`` is called.
    If False, the process has already exited (returncode 0) once ``lines`` are
    drained. If ``exits_on_terminate`` is False, only ``kill`` makes a running
    process "exit" -- simulating one that ignores SIGTERM.
    """

    def __init__(self, lines=(), running=True, exits_on_terminate=True):
        self.returncode = None
        self.terminated = False
        self.killed = False
        self._exits_on_terminate = exits_on_terminate
        self._exited = asyncio.Event()
        if not running:
            self.returncode = 0
            self._exited.set()
        self.stdout = self._stdout(lines)

    async def _stdout(self, lines):
        for line in lines:
            yield line
        await self._exited.wait()

    async def wait(self):
        await self._exited.wait()
        return self.returncode

    def terminate(self):
        self.terminated = True
        if self._exits_on_terminate:
            self.returncode = 0
            self._exited.set()

    def kill(self):
        self.killed = True
        self.returncode = -9
        self._exited.set()


class TestStreamingController(object):
    def test_init_requires_target_script_interpreter(self):
        with pytest.raises(TypeError):
            StreamingController()

    def test_init_rejects_negative_restart_delay(self):
        pool = MockPool()
        with pytest.raises(InvariantError):
            StreamingController(
                target=pool,
                script="script.py",
                interpreter=sys.executable,
                restart_delay=-1,
            )

    def test_init_stores_arguments(self):
        pool = MockPool()
        controller = StreamingController(
            target=pool,
            script="script.py",
            interpreter=sys.executable,
            restart_delay=5,
        )
        assert controller.target is pool
        assert controller.script == "script.py"
        assert controller.interpreter == sys.executable
        assert controller.restart_delay == 5

    def test_stream_demand_applies_parsed_values(self, tmp_path, caplog):
        script = write_script(
            tmp_path,
            """
            print(10)
            print(20.5)
            print(-3)
            """,
        )
        pool = MockPool()
        controller = StreamingController(
            target=pool, script=script, interpreter=sys.executable
        )

        with caplog.at_level(logging.WARNING, logger="cobald.controller.streaming"):
            asyncio.run(controller._stream_demand())

        # negative demand is clamped to 0 (and applied), not ignored
        assert pool.demand == 0
        assert "negative demand" in caplog.text

    def test_stream_demand_skips_unparsable_lines(self, tmp_path, caplog):
        script = write_script(
            tmp_path,
            """
            print("not-a-number")
            print(42)
            """,
        )
        pool = MockPool()
        controller = StreamingController(
            target=pool, script=script, interpreter=sys.executable
        )

        with caplog.at_level(logging.WARNING, logger="cobald.controller.streaming"):
            asyncio.run(controller._stream_demand())

        assert pool.demand == 42
        assert "not-a-number" in caplog.text

    def test_run_survives_repeated_spawn_failures(self, tmp_path, caplog):
        # example with not existing script
        pool = MockPool()
        controller = StreamingController(
            target=pool,
            script="unused.py",
            interpreter=str(tmp_path / "does-not-exist"),
            restart_delay=0.05,
        )

        with caplog.at_level(logging.ERROR, logger="cobald.controller.streaming"):
            asyncio.run(run_briefly(controller.run, duration=0.3))

        assert "streaming controller subprocess failed" in caplog.text

    def test_run_restarts_after_script_exits(self, monkeypatch):
        # fake create_subprocess_exec to avoid actually spawning a process
        spawn_count = 0
        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal spawn_count
            spawn_count += 1
            return FakeProcess(running=False)

        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", fake_create_subprocess_exec
        )

        # actual test
        pool = MockPool()
        controller = StreamingController(
            target=pool, script="s.py", interpreter=sys.executable, restart_delay=0.01
        )

        asyncio.run(run_briefly(controller.run, duration=0.1))

        assert spawn_count >= 2

    def test_stream_demand_terminates_process_on_cancellation(self, monkeypatch):
        # fake create_subprocess_exec to avoid actually spawning a process
        proc = FakeProcess(lines=[b"1\n"])
        async def fake_create_subprocess_exec(*args, **kwargs):
            return proc

        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", fake_create_subprocess_exec
        )

        # actual test
        pool = MockPool()
        controller = StreamingController(
            target=pool, script="s.py", interpreter=sys.executable
        )

        # cancel it after short time and check that the process was terminated (but not killed)
        asyncio.run(run_briefly(controller._stream_demand, duration=0.05))

        assert proc.terminated is True
        assert proc.killed is False

    def test_stream_demand_kills_process_that_ignores_terminate(self, monkeypatch):
        proc = FakeProcess(lines=[b"1\n"], exits_on_terminate=False)
        original_wait_for = asyncio.wait_for

        # fake create_subprocess_exec to avoid actually spawning a process
        # fake wait_for to avoid waiting too long for the process to exit
        async def fake_create_subprocess_exec(*args, **kwargs):
            return proc

        def fast_wait_for(coro, timeout):
            # keep the test fast without changing the code under test
            return original_wait_for(coro, 0.05)

        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", fake_create_subprocess_exec
        )
        monkeypatch.setattr(asyncio, "wait_for", fast_wait_for)

        # actual test
        pool = MockPool()
        controller = StreamingController(
            target=pool, script="s.py", interpreter=sys.executable
        )

        asyncio.run(run_briefly(controller._stream_demand, duration=0.05))

        assert proc.terminated is True
        assert proc.killed is True
