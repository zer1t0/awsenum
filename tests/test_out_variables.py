import awsenum
import json
import os

dir_path = os.path.dirname(__file__)

api = awsenum.apidef.load_api()

"""
def test_ec2_describe_client_vpn_endpoints_out_variable():
    value = extract_variable(
        "ec2",
        "describe_client_vpn_endpoints",
        "ec2_describe_client_vpn_endpoints"
    )
    assert value == ["cvpn-endpoint-123456789123abcde"]

def test_ec2_describe_vpcs_out_variable():
    value = extract_variable(
        "ec2",
        "describe_vpcs",
        "ec2_describe_vpcs",
    )
    assert value == ["vpc-0e9801d129EXAMPLE", "vpc-06e4ab6c6cEXAMPLE"]
"""

def test_amplifybackend_list_s3_buckets():
    _test_out_variable_value(
        "amplifybackend",
        "list-s3-buckets",
        "s3-buckets-names",
    )

def test_ec2_describe_instances_out_variable():
    _test_out_variable_value(
        "ec2",
        "describe-instances",
        "ec2-instances-ids",
    )

def test_ecs_list_clusters_out_variable():
    _test_out_variable_value("ecs", "list-clusters", "ecs-clusters-arns")

def test_ecs_list_tasks_out_variable():
    _test_out_variable_value(
        "ecs",
        "list-tasks",
        "ecs-cluster-tasks",
        version=0
    )

def test_ecs_list_services_out_variable():
    _test_out_variable_value("ecs", "list-services", "ecs-cluster-services")

def test_iam_get_policy_out_variable():
    _test_out_variable_value(
        "iam",
        "get-policy",
        "iam-policy-versions",
        variable_file="iam-policy-versions_get-policy"
    )

def test_iam_list_attached_role_policies_out_variable():
    _test_out_variable_value(
        "iam",
        "list-attached-role-policies",
        "iam-policies-arns",
        variable_file="iam-policies-arns_list-attached-role-policies"
    )

def test_iam_list_policies_policies_arns_out_variable():
    _test_out_variable_value("iam", "list-policies", "iam-policies-arns")

def test_iam_list_policies_policies_versions_out_variable():
    _test_out_variable_value(
        "iam",
        "list-policies",
        "iam-policies-versions",
        variable_file="iam-policies-versions_list-policies",
    )

def test_iam_list_policy_versions_out_variable():
    _test_out_variable_value(
        "iam",
        "list-policy-versions",
        "iam-policy-versions"
    )

def test_iam_list_role_policies_out_variable():
    _test_out_variable_value("iam", "list-role-policies", "iam-role-policies")

def test_iam_list_roles_out_variable():
    _test_out_variable_value("iam", "list-roles", "iam-rolenames")

def test_iam_list_users():
    _test_out_variable_value("iam", "list-users", "iam-usernames")

def test_lambda_list_functions_out_variable():
    _test_out_variable_value(
        "lambda",
        "list-functions",
        "lambda-functions-names"
    )

def test_s3_list_buckets():
    _test_out_variable_value("s3", "list-buckets", "s3-buckets-names")


def test_secretsmanager_list_secrets_out_variable():
    _test_out_variable_value(
        "secretsmanager",
        "list-secrets",
        "secretsmanager-secrets-arns",
    )

def _test_out_variable_value(
        service,
        operation,
        varname,
        version=0,
        response_file=None,
        variable_file=None
):
    value = extract_variable(
        service,
        operation,
        varname,
        version=version,
        response_file=response_file
    )
    assert value == load_variable(varname, variable_file)

def extract_variable(
        service,
        operation,
        varname,
        version=0,
        response_file=None
):
    response_file = response_file or "{}-{}".format(service, operation)

    operation_obj = api[service][operation]
    varpath = operation_obj["versions"][version]["outvars"][varname]

    response = load_response_sample(response_file)
    return awsenum.brute.extract_variable_value(
        varpath,
        response
    )

def load_response_sample(name):
    filepath = os.path.join(dir_path, "samples/responses/{}.json".format(name))
    return load_json(filepath)

def load_variable(varname, filename=None):
    filename = filename or varname
    filepath = os.path.join(
        dir_path, "samples/variables/{}.json".format(filename)
    )
    return load_json(filepath)[varname]


def load_json(filepath):
    with open(filepath) as fi:
        return json.load(fi)
