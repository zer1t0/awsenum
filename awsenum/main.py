#!/usr/bin/env python3

import logging

from . import apidef as apidefmod
from . import awsaccount
from . import client as clientmod
from . import args as argsmod
from . import brute as brutemod
from . import utils


logger = logging.getLogger(__name__)

def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass

def _main():
    args = argsmod.parse_args()
    init_log(args.verbosity)

    api = load_api_from_args(args)
    if not api:
        logger.error(
            "No operation was selected to test. "
            "Maybe you indicate an incorrect filter."
        )
        return

    if "list" in args:
        main_inspect_api(args, api)
    else:
        main_brute(args, api)


def init_log(verbosity=0, log_file=None):

    restrict_libraries_debug = True

    if verbosity == 1:
        level = logging.INFO
    elif verbosity > 1:
        level = logging.DEBUG
        if verbosity > 2:
            restrict_libraries_debug = False
    else:
        level = logging.WARN

    logging.basicConfig(
        level=level,
        filename=log_file,
        format="%(levelname)s:%(name)s:%(message)s"
    )

    if restrict_libraries_debug:
        # Suppress boto INFO.
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('nose').setLevel(logging.WARNING)

        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def main_inspect_api(args, api):
    if args.list is not None:
        max_level = args.list
    else:
        max_level = "operation"

    for service_name, service in api.items():
        if max_level == "service":
            print(service_name)
            continue

        for operation_name, operation in service.items():
            if max_level == "operation":
                print(service_name, operation_name)
                continue

            for version in operation["versions"]:
                version_msg = [service_name, operation_name]
                scope = version["scope"]
                invar = version["invar"]["name"]
                outvars = version["outvars"].keys()

                version_msg.append("scope:{}".format(scope))
                version_msg.append("invar:{}".format(invar))
                version_msg.append("outvars:{}".format(",".join(outvars)))

                print(" ".join(version_msg))



def main_brute(args, api):
    try:
        account = awsaccount.resolve_aws_account(
            args.profile,
            access_key=args.access_key,
            secret_key=args.secret_key,
            session_token=args.session_token,
            region=args.region,
        )
    except awsaccount.AccountError as e:
        logger.error(e)
        return

    logger.info("AWS Access key: %s", account.access_key)
    logger.info("Region: %s", account.region)

    client_provider = clientmod.ClientProvider(
        account,
        connect_timeout=args.connect_timeout/1000,
        read_timeout=args.read_timeout/1000,
        max_retries=args.max_retries,
    )

    if logger.getEffectiveLevel() <= logging.INFO:
        user_id, user_account, arn = clientmod.get_caller_identity(
            client_provider
        )
        logger.info("User ID: %s", user_id)
        logger.info("Account: %s", user_account)
        logger.info("ARN: %s", arn)

    if args.vars_file:
        try:
            variables = utils.load_yaml(args.vars_file)
        except OSError as e:
            logger.error(
                "Error opening variables file '%s': %s",
                args.vars_file, e
            )
            return

        if not isinstance(variables, dict):
            logger.error(
                "Variables file '%s' must be a"
                " dictionary containing the variables",
                args.vars_file
            )
            return
    else:
        variables = {}


    results = brutemod.brute(
        api,
        client_provider,
        variables,
        workers=args.workers,
        recurse=not args.non_recursive,
    )

    if args.results_filepath:
        results_filepath = args.results_filepath
    else:
        results_filepath = "awsenum-{}.json".format(
            utils.now_datetime().strftime("%Y-%m-%d-%H-%M-%S")
        )

    try:
        utils.save_json(results, results_filepath)
    except OSError as e:
        logging.error("Error saving results in '{}': {}".format(
            results_filepath, e
        ))



COMMON_SERVICES = [
    "acm",
    "acm-pca",
    "autoscaling",
    "cloudfront",
    "cognito-identity",
    "cognito-idp",
    "cognito-sync",
    "dynamodb",
    "ebs",
    "ec2",
    "ecs",
    "elasticache",
    "elasticbeanstalk",
    "glacier",
    "iam",
    "kinesis",
    "lambda",
    "lightsail",
    "rds",
    "s3",
    "sns",
    "sqs",
]

def load_api_from_args(args):

    allowed_scopes = ["private"]
    if args.allow_public:
        allowed_scopes.append("public")

    allowed_services = args.allowed_services or COMMON_SERVICES

    return apidefmod.load_api(
        allowed_services=allowed_services,
        excluded_services=args.excluded_services,
        allowed_operations=args.allowed_operations,
        excluded_operations=args.excluded_operations,
        allowed_scopes=allowed_scopes,
    )
