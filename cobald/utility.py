import asyncio
import typing

from .interfaces.controller import Controller
from .interfaces.actor import Actor


def schedule_pipelines(event_loop: asyncio.AbstractEventLoop, *leaves: Controller):
    seen = {None}  # type: typing.Set[typing.Optional[Controller]]
    for leave in leaves:
        this = leave
        while this not in seen:
            seen.add(this)
            if isinstance(this, Actor):
                this.mount(event_loop)
            this = getattr(this, 'target', None)  # type: typing.Optional[Controller]
