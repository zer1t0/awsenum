
import boto3
from threading import Lock
from botocore.endpoint import MAX_POOL_CONNECTIONS
import botocore.client


def get_caller_identity(client_provider):
    resp = client_provider.get_client("sts").get_caller_identity()
    return resp["UserId"], resp["Account"], resp["Arn"]


class ClientProvider:

    def __init__(
            self,
            account,
            verify=True,
            connect_timeout=5,
            read_timeout=60,
            max_retries=2,
    ):
        self.account = account
        self.verify = verify

        # there is a problem with the read_timeout for big requests
        # the read timeout is reached, and the client retries after sleeping
        # for a while, bad thing is that sleeping increases exponentially, so
        # first is 2s, then 4s, then 8s, then 16s,
        self.client_config = botocore.client.Config(
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries={'max_attempts': max_retries},
            max_pool_connections=MAX_POOL_CONNECTIONS * 2
        )
        self.client_lock = Lock()
        self.clients = {}


    def get_client(self, service):
        with self.client_lock:
            return self._get_client(service)

    def _get_client(self, service):
        try:
            return self.clients[service]
        except KeyError:
            self.clients[service] = boto3.client(
                service,
                aws_access_key_id=self.account.access_key,
                aws_secret_access_key=self.account.secret_key,
                aws_session_token=self.account.session_token,
                region_name=self.account.region,
                verify=self.verify,
                config=self.client_config,
            )

        return self.clients[service]

