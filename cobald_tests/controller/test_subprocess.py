import asyncio
import contextlib
import logging
import sys

from cobald.controller.subprocess import SubprocessController

from ..mock.pool import MockPool


async def run_briefly(coro, duration):
    """Run a coroutine, cancelling it after ``duration``"""
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(coro, timeout=duration)


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


class TestSubprocessController:
    def test_run_survives_repeated_spawn_failures(self, tmp_path, caplog):
        # example with not existing script
        pool = MockPool()
        controller = SubprocessController(
            target=pool,
            command=[str(tmp_path / "does-not-exist"), "unused.py"],
            restart_delay=0.05,
        )

        with caplog.at_level(logging.ERROR, logger="cobald.controller.subprocess"):
            asyncio.run(run_briefly(controller.run(), duration=0.3))

        assert "subprocess controller subprocess failed" in caplog.text

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
        controller = SubprocessController(
            target=pool, command=[sys.executable, "s.py"], restart_delay=0.01
        )

        asyncio.run(run_briefly(controller.run(), duration=0.1))

        assert spawn_count >= 2

    def test_stream_demand_terminates_process_on_cancellation(self, monkeypatch):
        # fake create_subprocess_exec to avoid actually spawning a process
        # (constructed lazily: asyncio.Event() binds to the running loop at
        # creation time on Python <=3.9, so it must not be created before
        # asyncio.run() starts the loop)
        proc = None

        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal proc
            proc = FakeProcess(lines=[b"1\n"])
            return proc

        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", fake_create_subprocess_exec
        )

        # actual test
        pool = MockPool()
        controller = SubprocessController(target=pool, command=[sys.executable, "s.py"])

        # cancel after a short time and check the process was terminated
        # (but not killed)
        asyncio.run(run_briefly(controller._stream_demand(), duration=0.05))

        assert proc.terminated is True
        assert proc.killed is False

    def test_stream_demand_kills_process_that_ignores_terminate(self, monkeypatch):
        proc = None
        original_wait_for = asyncio.wait_for

        # fake create_subprocess_exec to avoid actually spawning a process
        # fake wait_for to avoid waiting too long for the process to exit
        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal proc
            proc = FakeProcess(lines=[b"1\n"], exits_on_terminate=False)
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
        controller = SubprocessController(target=pool, command=[sys.executable, "s.py"])

        asyncio.run(run_briefly(controller._stream_demand(), duration=0.05))

        assert proc.terminated is True
        assert proc.killed is True
