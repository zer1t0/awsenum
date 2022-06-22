# awsenum

awsenum is a tool to identify what permissions your account has in AWS by bruteforcing the different operations and check what can you perform. It is only limited to read operations.

## Installation

```
cd awsenum/
pip install .
```

## Add bash completion

For the current user:
```
register-python-argcomplete awsenum >> ~/.bashrc
```

For the current session:
```
eval "$(register-python-argcomplete awsenum)"
```

## Usage examples

Enumerate the most common services:
```
awsenum
```

Enumerate with alternative AWS profile:
```
awsenum --profile johnny
```

### Selecting services and operations

In case you want so select the services you want to check, you can use the `-s/--service` and `--exclude-service` parameters. Here are some examples:

Enumerate all the AWS services:
```
awsenum -s '*'
```

Enumerate one service:
```
awsenum -s s3
```

Enumerate family of services:
```
awsenum -s 'sagemaker*'
```

Enumerate several services:
```
awsenum -s ec2 s3
```

You can also select specific operations per service with `--operation` and `--exclude-operation`. For example to only list s3 buckets:
```
awsenum -s ec2 --operation 'describe-*'
```

### Inspecting checked services and operations

If you want to know what operations are going to be checked, you can use the `--list` parameter with any of the previous filters to list the selected operations, rather than actually do the check:

```
$ awsenum -s s3 --operation 'list-*' --list
s3 list-bucket-analytics-configurations
s3 list-bucket-intelligent-tiering-configurations
s3 list-bucket-inventory-configurations
s3 list-bucket-metrics-configurations
s3 list-buckets
s3 list-multipart-uploads
s3 list-object-versions
s3 list-objects
s3 list-objects-v2
s3 list-parts
```

You can also only list the services, to for example, know what services are checked by default (this list may change in the future):

```
$ awsenum --list service
acm
acm-pca
autoscaling
cloudfront
cognito-identity
cognito-idp
cognito-sync
dynamodb
ebs
ec2
ecs
elasticache
elasticbeanstalk
glacier
iam
kinesis
lambda
lightsail
rds
s3
sns
sqs
```

### Using variables

As you may know, some AWS operation need parameters to retrieve information, for example `list-objects` from a s3 bucket needs the bucket name. This information can be retrieved from other API operations like s3 `list-buckets` (and even from others like amplifybackend `list-s3-buckets`). Therefore, the result of some operation calls is stored in variables that can be used for other operation calls. You can see it like a publish-subscribe flow.

In this example, the `list-buckets` operation will store the buckets names on the `s3-buckets-names` variable, which will be used by `list-objects` to enumerate the objects of each bucket.

What happens is the next:

```
s3:list-buckets --> s3-buckets-names --.--> s3:list-objects (Bucket=test1)
                   ["test1", "test2"]  |
                                       '--> s3:list-objects (Bucket=test2)
```

So the result will be something like this:
```
$ awsenum -s s3 --operation list-buckets list-objects
s3 list-buckets
s3 list-objects (Bucket=test1)
s3 list-objects (Bucket=test2)
```

You can check the operation that generates and consumes each variable by using the `--list version` parameter.

```
$ awsenum -s s3 --operation list-buckets list-objects --list version
s3 list-buckets scope:private invar: outvars:s3-buckets-names
s3 list-objects scope:private invar:s3-buckets-names outvars:
```

You also can pass a variable from a json file if you want. For example, to check if you have access to some s3 buckets, you can create a file with the following content:
```
{
    "s3-buckets-names": [
        "test1",
        "test2"
    ]
}
```

And then pass it to the program and select the proper operation:
```
$ awsenum -s s3 --operation list-objects-v2 --vars-file variables.json
s3 list-objects-v2 (Bucket=test2joadijfoisadjiofjd)
s3 list-objects-v2 (Bucket=testaskldfjaiopsdcnoidc)
```


## The API meta

The relations between AWS API operations (by using variables) are specified in the `api-meta.yml` file. This file includes information about each operation so the program can process it correctly.

In the file there are 3 main types of items in hierarchy:

- The AWS services (like s3, ec2, ...)
- The operations (like list-buckets, describe-instances, ...)
- The operation versions

The operation versions are the different variations of a operation based on its parameters. For example, the iam get-user operation can receive or not an username as parameter, so it has two versions, like the following:

```yaml
  get-user:
    versions:
      - {}
      - invar: iam-usernames
        args:
          UserName:
            invar_path: ""
            mode: foreach
```

This indicates that the `get-user` operation has two versions, an empty version that means it receives no parameters, and a version that depends on the variable `iam-usernames` (that is a list of usernames). The empty version is the default in case none version is specified, but if you specified another version, you have to declare the empty version explicitly, in case you want use it.

In the second version there is the argument `UserName` with the mode `foreach`, thus this argument will take each of the username of the list and tested it in different calls, instead of set `UserName` parameter as a list of usernames. The other interesting parameter here is `invar_path` that indicates the [jmespath](https://jmespath.org/) used to take the value of the parameter from the variable, in this case is empty since we want take the full value (for each username).

It is also possible to specify a mode in the invar variable, in case is needed. For example if we have the following variable:
```json
{
    "iam-policies-versions": [
        {
            "versions": [
                "v2"
                "v1"
            ],
            "policy": "arn:aws:iam::123456789012:policy/test-policy"
        },
        {
            "versions": [
                "v1",
            ],
            "policy": "arn:aws:iam::123456789012:policy/admin-policy"
        }
    ]
}
```

We may need to iterate over each policy and then over each version of policy in order to get pairs policy-version. This is the case in `get-policy-version`, so we specify the `foreach` mode in the variable.

```yaml
  get-policy-version:
    versions:
      .. # stripped
      - invar:
          name: iam-policies-versions
          mode: foreach
        args:
          PolicyArn:
            invar_path: "policy"
            mode: single

          VersionId:
            invar_path: "versions"
            mode: foreach
```

In this case, we iterate over each policy of the variable and for the `PolicyArn` parameter we take the `policy` keyword as a whole (`single` mode) and we iterate over each value in `versions` and take each one for VersionId, for testing in a different call. So in this case we will finish with the following combinations:

- PolicyArn=arn:aws:iam::123456789012:policy/test-policy VersionId=v1
- PolicyArn=arn:aws:iam::123456789012:policy/test-policy VersionId=v2
- PolicyArn=arn:aws:iam::123456789012:policy/admin-policy VersionId=v1


Going back to the usernames case, the `iam-usernames` variable is created by `list-users` as is shown next:
```yaml
  list-users:
    outvars:
      iam-usernames: "response.Users[].UserName"
```

In this case, the `list-users` has no explicit versions declared, so an empty version will be used by default, without parameters. But what is interesting is that `list-users`, in case of being successful, will generate the variable `iam-usernames`. This is specified in the `outvars` section which specifies the variable name and the jmespath used to built in base on the response. The `outvars` section can be specified by version or by operation, in this last case will apply to all its versions.

So if we want to list the usernames and try to get each one, we will get the following output:
```
$ awsenum -s iam --operation list-users get-user
iam list-users
iam get-user
iam get-user (UserName=Administrator)
iam get-user (UserName=iamtest)
```

You should also notice the `response` field as root in the `iam-usernames` path in `list-users`, that indicates that the fields are take from the response. It is also possible to use the `args` root field to take the values from the arguments. For example, the following example uses both arguments and response to built the variable value:

```yaml
  list-role-policies:
    ... # stripped
    outvars:
      iam-role-policies: "{role: args.RoleName, policies: response.PolicyNames}"
```


There is a couple more of keywords (at this moment). The first one is `scope`, that can be private or public. The scope `public` means that the operation returns information that is not specific for the target account, but for any user in AWS, and many of them retrieve a lot of information. Therefore, by default they are not considered relevant and not used, but you can allow them with the `--allow-public` flag if you want. Some public operations are `ec2 describe-host-reservation-offerings` or `route53 get-checker-ip-ranges`.


The another keyword is `allowed_client_error` that specifies an error that is considered a valid operation call. For example in `get-bucket-website` an error is retrieved if the bucket is not used to host a website, and returns a not found error, but we consider this a valid call, since is not denied (if you have permissions). So this is how is it specified:

```yaml
get-bucket-website:
    allowed_client_error: NoSuchWebsiteConfiguration
    .. # stripped
```

This is the explanation about the meta API file, that, unfortunately, is still far from being complete.
