import fnmatch
from abc import ABC, abstractmethod


def create_service_filter(
        allowed_services=None,
        excluded_services=None,
):
    excluded_services = excluded_services or []
    allowed_services = allowed_services or []

    validators = []

    if excluded_services:
        validators.append(NotFilter(ServiceFilter(excluded_services)))

    if allowed_services:
        validators.append(ServiceFilter(allowed_services))

    return AndFilter(validators)


def create_operation_filter(
        allowed_operations=None,
        excluded_operations=None,
):
    allowed_operations = allowed_operations or []
    excluded_operations = excluded_operations or []

    validators = []

    if excluded_operations:
        validators.append(NotFilter(OperationFilter(excluded_operations)))

    if allowed_operations:
        validators.append(OperationFilter(allowed_operations))

    return AndFilter(validators)


def create_version_filter(
        scopes=None
):
    scopes = scopes or []

    if scopes:
        return ScopeFilter(scopes)
    return TrueFilter()


class Filter(ABC):

    @abstractmethod
    def filter(self, *args, **kwargs):
        pass

    @abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        return str(self)

class TrueFilter(Filter):

    def filter(self, *args, **kwargs):
        return True

    def __str__(self):
        return "{}".format(
            self.__class__.__name__,
        )

class AndFilter(Filter):

    def __init__(self, subvalidators):
        super().__init__()
        self.subvalidators = subvalidators

    def filter(self, *args, **kwargs):
        for subvalidator in self.subvalidators:
            if not subvalidator.filter(*args, **kwargs):
                return False

        return True

    def __str__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self.subvalidators
        )

class NotFilter(Filter):

    def __init__(self, subvalidator):
        super().__init__()
        self.subvalidator = subvalidator

    def filter(self, *args, **kwargs):
        return not self.subvalidator.filter(*args, **kwargs)

    def __str__(self):
        return "{}(not {})".format(
            self.__class__.__name__,
            self.subvalidator
        )

class ScopeFilter(Filter):

    def __init__(self, scopes):
        super().__init__()
        self.scopes = scopes

    def filter(self, version, *args, **kwargs):
        return version["scope"] in self.scopes

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.scopes)

class ServiceFilter(Filter):

    def __init__(self, services):
        super().__init__()
        self.services = services

    def filter(self, service, *args, **kwargs):
        return _there_is_some_fnmatch(service, self.services)

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.services)

class OperationFilter(Filter):

    def __init__(self, operations):
        super().__init__()
        self.operations = operations

    def filter(self, operation, *args, **kwargs):
        return _there_is_some_fnmatch(operation, self.operations)

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.operations)


def _there_is_some_fnmatch(name, filters):
    if not filters:
        return True

    for filt in filters:
        if fnmatch.fnmatch(name, filt):
            return True

    return False
