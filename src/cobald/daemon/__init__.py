from .runners.service import ServiceRunner, service

#: The runner invoked on daemon startup
runtime = ServiceRunner()

__all__ = ["runtime", "service"]
