
import logging
import os
import botocore
import botocore.loaders
from .normalize import normalize_api
from . import filters
from .. import utils


logger = logging.getLogger(__name__)


def load_api(
        allowed_services=None,
        excluded_services=None,
        allowed_operations=None,
        excluded_operations=None,
        allowed_scopes=None,
):
    service_filter = filters.create_service_filter(
        allowed_services=allowed_services,
        excluded_services=excluded_services,
    )

    operation_filter = filters.create_operation_filter(
        allowed_operations=allowed_operations,
        excluded_operations=excluded_operations,
    )

    version_filter = filters.create_version_filter(
        scopes=allowed_scopes
    )

    api = _load_api(
        service_filter=service_filter,
        operation_filter=operation_filter,
        version_filter=version_filter,
    )

    return api


def _load_api(
        service_filter,
        operation_filter,
        version_filter
):

    # we filter each part of the API individually and incrementally
    # (service, operation, version) so we reduce the loading time
    # which is specially helpful to avoid lag in command completion

    base = _load_base(
        service_filter=service_filter,
        operation_filter=operation_filter,
    )

    # we also filter the service and operations in meta_api so we don't get
    # warnings for adding operations that are not in the base API, we don't
    # filter versions yet since if we do, we don't know when normalize if no
    # versions were specified or weren't create, so normalization will recreate
    # them all again, and versions filtered for public scope will be recreated
    metadata = _load_metadata(
        service_filter=service_filter,
        operation_filter=operation_filter,
    )

    api = normalize_api(_build_api(base, metadata))
    # once we have the final API, we filter the versions
    api = _filter_api_versions(
        api,
        version_filter=version_filter
    )

    api = _set_all_info_in_versions(api)

    return api


def _set_all_info_in_versions(api):
    for _, operations in api.items():
        for _, op_data in operations.items():
            allowed_client_error = op_data.pop("allowed_client_error")
            op_outvars = op_data.pop("outvars")

            for version in op_data["versions"]:
                version["allowed_client_error"] = allowed_client_error

                for varname, varpath in op_outvars.items():
                    if varname not in version["outvars"]:
                        version["outvars"][varname] = varpath


    return api


def _load_base(service_filter, operation_filter):
    base = {}
    for service in list_base_services(service_filter=service_filter):
        base[service] = list_base_service_operations(
            service,
            operation_filter=operation_filter
        )

    return base

def list_base_services(service_filter):
    return [
        s
        for s in list_all_base_services()
        if service_filter.filter(service=s)
    ]

def list_all_base_services():
    return botocore.loaders.Loader().list_available_services("service-2")

def list_base_service_operations(service, operation_filter):
    return [
        op
        for op in _list_all_base_service_operations(service)
        if operation_filter.filter(operation=op)
    ]

def _list_all_base_service_operations(service):
    loader = botocore.loaders.Loader()
    api_version = loader.determine_latest_version(service, "service-2")
    full_path = os.path.join(service, api_version, "service-2")

    operations = [
       botocore.xform_name(op, "-")
       for op in loader.load_data(full_path).get("operations", [])
    ]

    return [op for op in operations if _is_read_operation(op)]

def _is_read_operation(operation):
    for read_prefix in READ_OPERATION_PREFIXES:
        if operation.startswith(read_prefix):
            return True

    return False


READ_OPERATION_PREFIXES = {
    "list-",
    "describe-",
    "get-",
    "search",
    "select",
    "query",
}

def _build_api(base, metadata):

    api = {}
    for service, operations in base.items():
        api[service] = {}
        for operation in operations:
            api[service][operation] = {}

    for service, operations in metadata.items():
        if service not in api:
            logger.warning(
                "%s service is not present in the base API",
                service
            )
            continue

        for operation, op_data in operations.items():
            if operation not in api[service]:
                logger.warning(
                    "%s %s operation is not present in the base API",
                    service, operation
                )
                continue

            api[service][operation] = op_data

    return api

def _load_metadata(
    service_filter,
    operation_filter,
):
    meta_api = _load_metadata_file()
    meta_api = _filter_metadata(
        meta_api,
        service_filter=service_filter,
        operation_filter=operation_filter,
    )
    return meta_api



def _load_metadata_file():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    meta_path = os.path.join(script_dir, "api-meta.yml")
    return normalize_api(utils.load_yaml(meta_path))


def _filter_metadata(
        api,
        service_filter,
        operation_filter,
):

    logger.debug("Service filter: %s", service_filter)
    logger.debug("Operation filter: %s", operation_filter)

    filtered_api = {}
    for service, operations in api.items():
        if not service_filter.filter(service=service):
            continue

        allowed_operations = {}
        for operation, op_data in operations.items():
            if not operation_filter.filter(operation=operation):
                continue

            allowed_operations[operation] = op_data

        if allowed_operations:
            filtered_api[service] = allowed_operations

    return filtered_api


def _filter_api_versions(
        api,
        version_filter,
):
    logger.debug("Version filter: %s", version_filter)

    filtered_api = {}
    for service, operations in api.items():
        allowed_operations = {}
        for operation, op_data in operations.items():
            op_data["versions"] = [
                version
                for version in op_data["versions"]
                if version_filter.filter(version=version)
            ]

            if op_data["versions"]:
                allowed_operations[operation] = op_data

        if allowed_operations:
            filtered_api[service] = allowed_operations

    return filtered_api
