from .base_runner import OrphanedReturn


async def return_trap(payload):
    """Wrapper to raise exception on unhandled return values"""
    value = await payload()
    if value is not None:
        raise OrphanedReturn(payload, value)
