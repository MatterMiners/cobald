import threading


from .base_runner import SubroutineRunner


class ThreadRunner(SubroutineRunner):
    flavour = threading

    def run(self):
        threads = []
        for subroutine in self._subroutines:
            thread = threading.Thread(target=subroutine)
            thread.daemon = True
        while True:
            for thread in threads:
                thread.join(timeout=1)
                if not thread.is_alive:
                    return
