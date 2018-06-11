import threading
import trio


from .base_runner import CoroutineRunner, SubroutineRunner
try:
    from . import *
except ImportError:
    pass


class MetaRunner(object):
    runners = {
        runner.flavour: runner for runner in CoroutineRunner.__subclasses__() + SubroutineRunner.__subclasses__()
    }

    def register_coroutine(self, coroutine, flavour=trio):
        self.runners[flavour].register_coroutine(coroutine)

    def register_subroutine(self, subroutine, flavour=threading):
        self.runners[flavour].register_subroutine(subroutine)

    def run(self):
        runners = [runner for runner in self.runners.values() if runner]
        if len(runners) == 1:
            runners[0].run()
        else:
            thread_runner = self.runners[threading]
            for runner in runners:
                if runner is not thread_runner:
                    thread_runner.register_subroutine(runner.run)
            thread_runner.run()
