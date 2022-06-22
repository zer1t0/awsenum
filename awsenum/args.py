
import argcomplete
import argparse

from . import awsaccount
from . import apidef

DEFAULT_CONNECT_TIMEOUT = 10000
DEFAULT_READ_TIMEOUT = 60000
DEFAULT_MAX_RETRIES = 2

def ServiceCompleter(**kwargs):
    return apidef.list_all_base_services()

def OperationCompleter(**kwargs):
    allowed_services = kwargs["parsed_args"].allowed_services
    excluded_services = kwargs["parsed_args"].excluded_services
    api_def = apidef.load_api(
        allowed_services=allowed_services,
        excluded_services=excluded_services,
    )
    allowed_operations = []
    for operations in api_def.values():
        allowed_operations.extend(operations)

    return allowed_operations


MAX_LEVEL_DEFAULT = "operation"

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--access-key",
        help="Access key for the API. "
        "If provided, secret key is also required."
    )

    parser.add_argument(
        "--secret-key",
        help="Secret key for the API."
    )

    parser.add_argument(
        "--session-token",
        help="Token for the API session."
    )

    parser.add_argument(
        "--profile",
        default="default",
        help="AWS profile to use in requests."
    ).completer = ProfileCompleter

    parser.add_argument(
        "--region",
        help="AWS region to inspect."
    )

    parser.add_argument(
        "-s", "--service",
        help="Services to check. "
        "Wildcard can be used to match several services.",
        nargs="+",
        dest="allowed_services",
        metavar="SERVICE",
    ).completer = ServiceCompleter

    parser.add_argument(
        "--exclude-service",
        help="Exclude services from check."
        " Wildcard can be used to match several services.",
        nargs="+",
        dest="excluded_services",
        metavar="SERVICE",
    ).completer = ServiceCompleter

    parser.add_argument(
        "--operation",
        help="Operation to check."
        " Wildcard can be used to match several operations.",
        nargs="+",
        dest="allowed_operations",
        metavar="operation",
    ).completer = OperationCompleter

    parser.add_argument(
        "--exclude-operation",
        help="Exclude operations from check."
        " Wildcard can be used to match several operations.",
        nargs="+",
        dest="excluded_operations",
        metavar="operation",
    ).completer = OperationCompleter

    parser.add_argument(
        "--allow-public",
        help="Also check the operations that retrieve information not related"
        " with your account.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--non-recursive",
        help="Avoid trigger new checks from results of others.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--vars-file",
        help="File with variables to use as input declared."
        " Can be JSON or YAML format.",
    )

    parser.add_argument(
        "-o", "--out",
        metavar="FILE",
        dest="results_filepath",
        help="File to write API calls results."
        " Default: awsenum-<datetime>.json."
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=10,
        help="Number of concurrent workers/threads to make requests."
    )

    parser.add_argument(
        "--connect-timeout",
        type=uint,
        default=DEFAULT_CONNECT_TIMEOUT,
        help="Request connection timeout, in milliseconds."
        " Default: {}.".format(DEFAULT_CONNECT_TIMEOUT),
    )

    parser.add_argument(
        "--read-timeout",
        type=uint,
        default=DEFAULT_READ_TIMEOUT,
        help="Request read timeout, in milliseconds."
        " Default: {}.".format(DEFAULT_READ_TIMEOUT),
    )

    parser.add_argument(
        "--max-retries",
        type=uint,
        default=DEFAULT_MAX_RETRIES,
        help="Number of retries after a timeout in request."
        " Default: {}.".format(DEFAULT_MAX_RETRIES)
    )

    parser.add_argument(
        "--list",
        help="List the selected services, operations or versions to check,"
        " instead of performing the enumeration.",
        nargs="?",
        choices=("service", "operation", "version"),

        # We suppress the argument by default so we can know when it is passed
        # by the user. So we have the following posibilites:
        # If list not in args namespace: not used.
        # If list is None: used without argument.
        # If list other: used with argument.
        default=argparse.SUPPRESS,
    )

    parser.add_argument(
        "-v",
        dest="verbosity",
        action="count",
        default=0,
        help="Increase verbosity level."
        " -v: Info. -vv: Debug. -vvv: Debug libraries."
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    return args

def ProfileCompleter(**kwargs):
    return awsaccount.list_profiles()

def uint(v):
    try:
        v = int(v)
        if v < 0:
            raise ValueError("")
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Must be a positive number"
        )
