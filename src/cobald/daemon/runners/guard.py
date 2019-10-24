import threading
import functools


def exclusive(via=threading.Lock):
    """
    Mark a callable as exclusive

    :param via: factory for a Lock to guard the callable

    Guards the callable against being entered again before completion.
    Explicitly raises a :py:exc:`RuntimeError` on violation.

    :note: If applied to a method, it is exclusive across all instances.
    """

    def make_exclusive(fnc):
        fnc_guard = via()

        @functools.wraps(fnc)
        def exclusive_call(*args, **kwargs):
            if fnc_guard.acquire(blocking=False):
                try:
                    return fnc(*args, **kwargs)
                finally:
                    fnc_guard.release()
            else:
                raise RuntimeError("exclusive call to %s violated")

        return exclusive_call

    return make_exclusive
