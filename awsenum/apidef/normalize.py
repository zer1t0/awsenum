
import logging
import jsonschema
import yaml
import os

logger = logging.getLogger(__name__)

def normalize_api(api):
    _validate_api(api)

    for service, operations in api.items():
        for operation, op_data in operations.items():
            api[service][operation] = _normalize_operation(
                service,
                operation,
                op_data
            )

    return api

def _validate_api(api):
    schema = _load_api_schema()
    jsonschema.validate(api, schema)

def _load_api_schema():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "aws-apischema.yml")
    with open(base_path) as fi:
        return yaml.safe_load(fi)

def _normalize_operation(service, operation, op_data):
    if not "allowed_client_error" in op_data:
        op_data["allowed_client_error"] = ""

    if not "outvars" in op_data:
        op_data["outvars"] = {}

    if "versions" not in op_data:
        op_data["versions"] = [{}]

    op_data["versions"] = _normalize_versions(op_data["versions"])

    return op_data


def _normalize_versions(versions):
    for i in range(len(versions)):
        versions[i] = _normalize_version(versions[i])

    return versions

def _normalize_version(version):
    if "scope" not in version:
        version["scope"] = "private"

    if "outvars" not in version:
        version["outvars"] = {}

    if "args" in version:
        args = version["args"]
        for arg_name in args:
            arg_value = args[arg_name]
            version["args"][arg_name] = _normalize_arg(arg_value)
    else:
        version["args"] = {}

    if "invar" not in version:
        version["invar"] = {
            "name": "",
            "mode": "single",
        }
    else:
        if isinstance(version["invar"], str):
            version["invar"] = {
                "name": version["invar"],
                "mode": "single",
            }
        elif "mode" not in version["invar"]:
            version["invar"]["mode"] = "single"

    return version

def _normalize_arg(arg_value):
    mode = arg_value.get("mode", "single")

    if "value" in arg_value:
        return {
            "value": arg_value["value"],
            "mode": mode,
        }

    return {
        "mode": mode,
        "invar_path": arg_value["invar_path"],
    }

