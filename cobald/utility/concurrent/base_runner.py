class CoroutineRunner(object):
    flavour = None

    def __init__(self):
        self._coroutines = []

    def register_coroutine(self, coroutine):
        self._coroutines.append(coroutine)

    def __bool__(self):
        return bool(self._coroutines)

    def run(self):
        raise NotImplementedError


class SubroutineRunner(object):
    flavour = None

    def __init__(self):
        self._subroutines = []

    def register_subroutine(self, subroutine):
        self._subroutines.append(subroutine)

    def __bool__(self):
        return bool(self._subroutines)

    def run(self):
        raise NotImplementedError
