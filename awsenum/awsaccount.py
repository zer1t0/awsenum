import botocore.client
import botocore.session

from collections import namedtuple

def resolve_aws_account(
        profile,
        access_key=None,
        secret_key=None,
        session_token=None,
        region=None
):
    if access_key or secret_key or session_token:
        account = AWSAccount(access_key, secret_key, session_token, region)
    else:
        account = get_account_from_profile(profile)
        if region:
            account.region = region

    if not account.access_key:
        raise AccountError("No access key, please specify one")

    if not account.secret_key:
        raise AccountError("No secret key, please specify one")

    if not account.region:
        raise AccountError("No region can be found, please specify one")

    return account

def list_profiles():
    return botocore.session.Session().available_profiles

def get_account_from_profile(profile):
    try:
        session = botocore.session.Session(profile=profile)
        creds = session.get_credentials()

        access_key = creds.access_key
        secret_key = creds.secret_key
        session_token = creds.token
        region = session._resolve_region_name(None, None)
        return AWSAccount(access_key, secret_key, session_token, region)
    except botocore.exceptions.ProfileNotFound:
        raise AccountError("Profile '{}' cannot be found".format(profile))

class AccountError(Exception):
    pass

class AWSAccount:

    def __init__(self, access_key, secret_key, session_token, region):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.region = region

