
from concurrent.futures import ThreadPoolExecutor, as_completed
import jmespath
import logging
import botocore
from itertools import chain

from . import operation as opmod

logger = logging.getLogger(__name__)


def brute(api, client_provider, variables, workers=10, recurse=True):
    pre_operations = get_api_pre_operations_per_invar(api)

    empty_variable = ("", {})
    new_operations = resolve_dependencies(
        pre_operations,
        chain((empty_variable,), variables.items())
    )

    if not recurse:
        pre_operations = {}

    pool = ThreadPoolExecutor(workers)
    results = {}

    tested_operations = set()

    try:
        while new_operations:
            ready_operations = []
            for op in new_operations:
                if op not in tested_operations:
                    tested_operations.add(op)
                    ready_operations.append(op)

            new_results, new_operations = run_brute_iteration(
                pool,
                client_provider,
                ready_operations,
                pre_operations,
            )
            results.update(new_results)

    except KeyboardInterrupt:
        pass

    return results


def get_api_pre_operations_per_invar(api):
    pre_operations = {"": []}

    for pre_operation in opmod.get_pre_operations(api):
        invar_name = pre_operation.input_variable.name
        try:
            pre_operations[invar_name].append(pre_operation)
        except KeyError:
            pre_operations[invar_name] = [pre_operation]

    return pre_operations

def resolve_dependencies(pre_operations, variables):
    operations = []
    for var_name, var_value in variables:
        operations.extend(
            resolve_dependency(pre_operations, var_name, var_value)
        )
    return operations

def resolve_dependency(pre_operations, var_name, var_value):
    if var_name not in pre_operations.keys():
        return []

    ready_operations = []
    for pre_operation in pre_operations[var_name]:
        ready_operations.extend(pre_operation.concretize(var_value))

    return ready_operations

class Variable:

    def __init__(self, name, value):
        self.name = name
        self.value = value

def run_brute_iteration(
        pool,
        client_provider,
        operations,
        pre_operations,
):
    threads = []
    results = {}
    for operation in operations:
        t = pool.submit(check_operation, client_provider, operation)
        threads.append(t)

    new_operations = []

    try:
        for check_op in as_completed(threads):
            try:
                operation, response = check_op.result()
                print("{} {} {}".format(
                    operation.service, operation.name, operation.args_str
                ))
                results[operation.id] = response

                for out_variable in operation.out_variables:
                    variable = extract_variable(
                        out_variable,
                        {"args": operation.args, "response": response},
                    )
                    logger.debug(
                        "%s outvar: %s=%s",
                        operation.id, variable.name, variable.value
                    )

                    new_operations.extend(resolve_dependency(
                        pre_operations, variable.name, variable.value
                    ))

            except CheckOperationError as ex:
                handle_check_operation_error(ex)

    except KeyboardInterrupt:
        new_operations = []

    return results, new_operations


def handle_check_operation_error(check_error):
    operation = check_error.operation
    try:
        raise check_error.inner_error
    except (
            botocore.exceptions.ParamValidationError,
            botocore.exceptions.ClientError,
            botocore.exceptions.EndpointConnectionError,
    ) as e:
        logger.debug("Error {} in {}: {}".format(
            get_class_path(e),
            operation.id,
            e
        ))

    except KeyboardInterrupt:
        raise

    except Exception as e:
        logger.warning("Error {} in {}: {}".format(
            get_class_path(e),
            operation.id,
            e
        ))

def is_connection_error(e):
    return isinstance(e, botocore.exceptions.EndpointConnectionError) or \
       isinstance(e, botocore.exceptions.ConnectTimeoutError)

    return False

# we use this method since there are classes that are defined in
# runtime and isinstance doesn't allow to compare
def get_class_path(obj):
    return "{}.{}".format(obj.__class__.__module__, obj.__class__.__name__)


def extract_variable(out_variable, response):
    name = out_variable.name
    value = extract_variable_value(out_variable.path, response)
    return Variable(name, value)

def extract_variable_value(path, response):
    return jmespath.search(path, response)


def check_operation(client_provider, operation):
    try:
        client = client_provider.get_client(operation.service)

        logger.info("Testing {} {} {}".format(
            operation.service, operation.name, operation.args_str
        ))

        py_op_name = operation.name.replace("-", "_")

        if client.can_paginate(py_op_name):
            paginator = client.get_paginator(py_op_name)
            response = paginator.paginate(**operation.args).build_full_result()
        else:
            response = getattr(client, py_op_name)(**operation.args)

        return operation, remove_response_metadata(response)
    except botocore.exceptions.ClientError as e:
        if operation.allowed_client_error:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == operation.allowed_client_error:
                return operation, {}

        raise CheckOperationError(operation, e)
    except Exception as e:
        raise CheckOperationError(operation, e)

class CheckOperationError(Exception):

    def __init__(self, operation, inner_error):
        super().__init__(str(inner_error))
        self.operation = operation
        self.inner_error = inner_error


def remove_response_metadata(response):
    try:
        del response["ResponseMetadata"]
    except KeyError:
        pass
    return response
