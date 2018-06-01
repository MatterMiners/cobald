import argparse
import asyncio
import logging
import platform
import sys

from .pool import ConcurrencyLimit, ConcurrencyAntiLimit

from ...controller.linear import LinearController
from ...decorator.buffer import Buffer
from ...decorator.logger import Logger
from ...decorator.limiter import Limiter
from ...decorator.coarser import Coarser
from ...utility import schedule_pipelines


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
    type=str,
    help='name of any concurrent resource that conflicts with `resource`',
)
CLI_resource.add_argument(
    'total',
    nargs='?',
    type=str,
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
    type=int,
    help='maximum increase or decrease of resources per second',
)
CLI_controller.add_argument(
    '--decrease',
    default=0.9,
    type=float,
    help='utilisation below which resources are decreased',
)
CLI_controller.add_argument(
    '--increase',
    default=0.95,
    type=float,
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
    options = CLI.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s (%(process)d) %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.critical('COBalD: condor_limits')
    logging.critical('%s %s (%s)', platform.python_implementation(), platform.python_version(), sys.executable)
    logging.warning('configuring components')
    if options.opponent or options.total:
        if not options.opponent or not options.total:
            raise RuntimeError('both opponent and total must be set together')
        try:
            total = float(options.total)
        except ValueError:
            total = options.total
        pool = ConcurrencyAntiLimit(
            resource=options.resource,
            opponent=options.opponent,
            total=total,
            pool=options.pool,
        )
    else:
        pool = ConcurrencyLimit(resource=options.resource, pool=options.pool)
    pool = Logger(pool, identifier='htcondor.limits')
    pool = Buffer(pool, window=30)
    if options.granularity != 1:
        pool = Coarser(pool, granularity=options.granularity)
    pool = Limiter(pool, minimum=options.granularity, maximum=options.limit)
    pool = LinearController(
        pool,
        low_utilisation=options.decrease, high_allocation=options.increase,
        rate=options.max_rate
    )
    logging.warning('registering components')
    schedule_pipelines(event_loop, pool)
    logging.warning('launching event loop...')
    event_loop.run_forever()


main()
