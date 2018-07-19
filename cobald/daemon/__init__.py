from ._runner import runner
from .service import ServiceRunner, service

runtime = ServiceRunner()

__all__ = ['runtime', 'service']
