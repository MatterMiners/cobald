import time
import logging
import subprocess

from collections import abc


def query_limits(query_command, key_transform):
    resource_limits = {}
    for item in subprocess.check_output(query_command, timeout=10, universal_newlines=True).splitlines():
        if '=' not in item:
            continue
        key, _, value = (value.strip() for value in item.partition('='))
        try:
            resource = key_transform(key)
        except ValueError:
            continue
        else:
            try:
                resource_limits[resource] = float(value)
            except ValueError:
                pass
    return resource_limits


class CondorQueryMapping(abc.Mapping):
    def __init__(self, pool: str = None, max_age: float = 30):
        self.pool = pool
        self.max_age = max_age
        self._valid_date = 0
        self._data = {}

    def __len__(self):
        if self._valid_date < time.time():
            self._query_data()
        return len(self._data)

    def __iter__(self):
        if self._valid_date < time.time():
            self._query_data()
        return iter(self._data)

    def __getitem__(self, item):
        if self._valid_date < time.time():
            self._query_data()
        return self._data[item]

    @staticmethod
    def _query_data():
        pass

    def __str__(self):
        if self._valid_date < time.time():
            self._query_data()
        return str(self._data)

    def __repr__(self):
        return '%s(pool=%s, max_age=%s)' % (self.__class__.__name__, self.pool, self.max_age)


class ConcurrencyConstraintView(CondorQueryMapping, abc.MutableMapping):
    def __init__(self, pool: str = None, max_age: float = 30):
        super().__init__(pool=pool, max_age=max_age)
        self._logger = logging.getLogger('condor_limits.constraints.%s' % pool)

    def __getitem__(self, resource: str) -> float:
        try:
            return super().__getitem__(resource)
        except KeyError:
            if '.' in resource:
                return self._data[resource.split('.')[0]]  # check parent group of resource
            raise

    def __delitem__(self, key):
        self._set_constraint(key, '')
        self._valid_date = 0

    def __setitem__(self, key: str, value: float):
        self._set_constraint(key, str(int(value)))
        self._valid_date = 0

    @staticmethod
    def _key_to_resource(key: str) -> str:
        if key.lower()[-6:] == '_limit':
            return key[:-6]
        raise ValueError

    def _query_data(self):
        query_command = ['condor_config_val', '-negotiator', '-dump', 'LIMIT']
        if self.pool:
            query_command.extend(('-pool', str(self.pool)))
        try:
            resource_limits = query_limits(query_command, key_transform=self._key_to_resource)
        except subprocess.CalledProcessError:
            return
        else:
            self._valid_date = self.max_age + time.time()
            self._data = resource_limits
            self._logger.debug('pool=%s, constraints=%r', self.pool, resource_limits)

    def _set_constraint(self, resource: str, constraint: str):
        reconfig_command = ['condor_config_val', '-negotiator']
        flush_command = ['condor_reconfig', '-negotiator']
        if self.pool:
            reconfig_command.extend(('-pool', str(self.pool)))
            flush_command.extend(('-pool', str(self.pool)))
        reconfig_command.extend(('-rset', '%s_LIMIT = %s' % (resource, constraint)))
        try:
            subprocess.check_call(reconfig_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            subprocess.check_call(flush_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
            self._logger.error('failed to constraint %r to %r', resource, constraint, exc_info=err)
        else:
            self._valid_date = 0


class ConcurrencyUsageView(CondorQueryMapping):
    def __init__(self, pool: str = None, max_age: float = 30):
        super().__init__(pool=pool, max_age=max_age)
        self._logger = logging.getLogger('condor_limits.usage.%s' % pool)

    def __getitem__(self, resource: str) -> float:
        try:
            return super().__getitem__(resource.replace('.', '_'))
        except KeyError:
            if '.' in resource:
                return self._data[resource.split('.')[0]]  # check parent group of resource
            raise

    @staticmethod
    def _key_to_resource(key: str) -> str:
        if key.startswith('ConcurrencyLimit_'):
            return key[17:]
        raise ValueError

    def _query_data(self):
        query_command = ['condor_userprio', '-negotiator', '-long']
        if self.pool:
            query_command.extend(('-pool', str(self.pool)))
        try:
            resource_usage = query_limits(query_command, key_transform=self._key_to_resource)
        except subprocess.CalledProcessError:
            return
        else:
            self._valid_date = self.max_age + time.time()
            self._data = resource_usage
            self._logger.debug('pool=%s, usage=%r', self.pool, resource_usage)


class PoolResources(CondorQueryMapping):
    def __init__(self, pool: str = None, max_age: float = 30):
        super().__init__(pool=pool, max_age=max_age)
        self._logger = logging.getLogger('condor_limits.resources.%s' % pool)

    def _query_data(self):
        query_command = ['condor_status']
        if self.pool:
            query_command.extend(('-pool', str(self.pool)))
        query_command.extend((
            "-startd",
            "-constraint", ' && '.join((
                'SlotType!="Dynamic"',  # Dynamic slots are part of entire machines which we already match
                'State=!="Owner"',  # Owner machines are unavailable
            )),
            "-af", "TotalSlotCpus", "TotalSlotMemory", "TotalSlotDisk", "Machine"
        ))
        data = {'cpus': 0, 'memory': 0, 'disk': 0, 'machines': 0}
        machines = set()
        try:
            for machine_info in subprocess.check_output(query_command, universal_newlines=True).splitlines():
                try:
                    cpus, memory, disk, machine = machine_info.split()
                except ValueError:
                    continue
                else:
                    data['cpus'] += float(cpus)
                    data['memory'] += float(memory)
                    data['disk'] += float(disk)
                    machines.add(machine)
        except subprocess.CalledProcessError:
            pass
        else:
            data['machines'] = len(machines)
            self._valid_date = self.max_age + time.time()
            self._data = data
            self._logger.debug('pool=%s, resources=%r', self.pool, data)

    def __repr__(self):
        return '%s(pool=%s, max_age=%s)' % (self.__class__.__name__, self.pool, self.max_age)


class PoolResourceView(object):
    def __init__(self, resource, pool_resources):
        self._resource = resource
        self._pool_resources = pool_resources

    def __int__(self):
        return int(self._pool_resources[self._resource])

    def __float__(self):
        return float(self._pool_resources[self._resource])

    def __sub__(self, other):
        return float(self) - other


__all__ = [ConcurrencyConstraintView.__name__, ConcurrencyUsageView.__name__, PoolResourceView.__name__]
