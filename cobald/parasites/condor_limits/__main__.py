import argparse
import asyncio

from ...interfaces.actor import Actor

from .pool import ConcurrencyLimit, ConcurrencyAntiLimit

from ...controller.linear import LinearController
from ...proxy.buffer import Buffer
from ...proxy.logger import Logger
from ...proxy.limiter import Limiter
from ...proxy.coarser import Coarser

CLI = argparse.ArgumentParser('HTCondor Concurrency Limit Balancer')
CLI_resource = CLI.add_argument_group('Resource Definition')
CLI_resource.add_argument(
    'resource',
    help='name of the concurrent resource to limit',
    type=str,
)
CLI_resource.add_argument(
    'opponent',
    nargs='?',
    help='name of any concurrent resource that conflicts with `resource`',
)
CLI_resource.add_argument(
    'total',
    nargs='?',
    help='the total underlying resources shared by `resource` and `opponent`. "'
         '"Must be a number or any of "cpus", "memory", "disk" or "machines"',
)
CLI_resource.add_argument(
    '--pool',
    default=None,
    type=str,
    help='name of the condor pool to manage',
)
CLI_controller = CLI.add_argument_group('Resource Control')
CLI_controller.add_argument(
    '--max-rate',
    default=8,
    help='maximum increase or decrease of resources per second',
)
CLI_controller.add_argument(
    '--decrease',
    default=0.9,
    help='utilisation below which resources are decreased',
)
CLI_controller.add_argument(
    '--increase',
    default=0.95,
    help='utilisation above which resources are increased',
)
CLI_controller.add_argument(
    '--limit',
    help='maximum limit for resource',
    type=int,
    default=float('inf')
)
CLI_controller.add_argument(
    '--granularity',
    help='maximum limit for resource',
    default=1,
    type=int,
)


def main():
    event_loop = asyncio.get_event_loop()
    components = []
    options = CLI.parse_args()
    if options.opponent or options.total:
        if not options.opponent or not options.total:
            raise RuntimeError('both opponent and total must be set together')
        try:
            total = float(options.total)
        except ValueError:
            total = options.total
        components.append(ConcurrencyAntiLimit(
            resource=options.resource,
            opponent=options.opponent,
            total=total,
            pool=options.pool,
        ))
    else:
        components.append(ConcurrencyLimit(resource=options.resource, pool=options.pool))
    components.append(Logger(components[-1], identifier='htcondor.limits'))
    components.append(Buffer(components[-1], window=30))
    if options.granularity != 1:
        components.append(Coarser(components[-1], granularity=options.granularity))
    components.append(Limiter(components[-1], minimum=options.granularity, maximum=options.limit))
    components.append(LinearController(
        components[-1],
        low_utilisation=options.decrease, high_consumption=options.increase,
        rate=options.max_rate
    ))
    for component in components:
        if isinstance(component, Actor):
            component.mount(event_loop)
    event_loop.run_forever()


main()
