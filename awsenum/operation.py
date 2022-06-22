import jmespath

class PreOperation:
    """Contains the definition of the operation to be completed with the
    variable dependencies.
    """

    def __init__(
            self,
            service,
            name,
            pre_args,
            out_variables,
            input_variable,
            allowed_client_error,
    ):
        self.service = service
        self.name = name
        self.pre_args = pre_args
        self.out_variables = out_variables
        self.input_variable = input_variable
        self.allowed_client_error = allowed_client_error

    def concretize(self, input_):
        return concretize_operations(self, input_)

    @property
    def input_mode(self):
        return self.input_variable.mode

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "PreOperation: {} {} ({})".format(
            self.service,
            self.name,
            self.input_variable.name
        )


def get_pre_operations(api_def):

    for service, operations in api_def.items():
        for op_name, op_data in operations.items():

            for version in op_data["versions"]:
                op_args = version["args"]
                input_variable = InVar(
                    version["invar"]["name"],
                    version["invar"]["mode"],
                )


                out_variables = [
                    OutVar(varname, varpath)
                    for varname, varpath in version["outvars"].items()
                ]
                allowed_client_error = version["allowed_client_error"]

                yield PreOperation(
                    service=service,
                    name=op_name,
                    pre_args=op_args,
                    out_variables=out_variables,
                    input_variable=input_variable,
                    allowed_client_error=allowed_client_error,
                )

def concretize_operations(pre_operation, input_):
    if pre_operation.input_mode == "single":
        input_ = [input_]

    for element in input_:
        for args in concretize_args(pre_operation.pre_args, element):
            yield Operation(
                service=pre_operation.service,
                name=pre_operation.name,
                args=args,
                out_variables=pre_operation.out_variables,
                allowed_client_error=pre_operation.allowed_client_error,
            )

def concretize_args(pre_args, input_):
    if not pre_args:
        yield {}
        return

    args_list = []
    for arg_name, arg_def in pre_args.items():
        values = get_pre_arg_values(arg_def, input_)
        args_list.append({"name": arg_name, "values": values})

    for args in args_cart_product(args_list):
        yield args


def get_pre_arg_values(arg_def, input_):
    if "value" in arg_def:
        values = arg_def["value"]
    else:
        if arg_def["invar_path"]:
            values = jmespath.search(arg_def["invar_path"], input_)
        else:
            values = input_

    if arg_def["mode"] != "foreach":
        values = [values]

    return values


# Adapted version of https://stackoverflow.com/a/12658055
def args_cart_product(args_list):
    bounds = [len(arg["values"]) for arg in args_list]

    for elem in lex_gen(bounds):
        yield {
            args_list[i]["name"]: args_list[i]["values"][elem[i]]
            for i in range(len(args_list))
        }

def lex_gen(bounds):
    # if at least one argument contains 0 values
    # then it is not possible to do the cartessian
    # product
    if 0 in bounds:
        return

    elem = [0] * len(bounds)
    while True:
        yield elem
        i = 0
        while elem[i] == bounds[i] - 1:
            elem[i] = 0
            i += 1
            if i == len(bounds):
                return
        elem[i] += 1

class InVar:

    def __init__(self, name, mode):
        self.name = name
        self.mode = mode

class OutVar:

    def __init__(self, name, path):
        self.name = name
        self.path = path


class Operation:
    """The concrete operation with the definitive arguments

    The attributes of this class cannot be changed once created, in order to
    hash work properly.
    """

    def __init__(
            self,
            service,
            name,
            args,
            out_variables,
            allowed_client_error
    ):
        self._service = service
        self._name = name
        self._args = args
        self.out_variables = out_variables
        self.allowed_client_error = allowed_client_error

    @property
    def service(self):
        return self._service

    @property
    def name(self):
        return self._name

    @property
    def args(self):
        return self._args

    @property
    def args_str(self):
        if not self.args:
            return ""

        args_str = []
        for k, v in self.args.items():
            args_str.append("{}={}".format(k, v))
        return "({})".format(",".join(args_str))

    @property
    def id(self):
        if self.args_str:
            return "{}.{} {}".format(
                self.service, self.name, self.args_str
            )

        return "{}.{}".format(
            self.service, self.name
        )

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.id

    def __hash__(self):
        return hash((
            self.service,
            self.name,
            make_hashable(self.args)
        ))

    def __eq__(self, other):
        return self.service == other.service \
            and self.name == other.name \
            and self.args == other.args

def make_hashable(obj):
    if isinstance(obj, list):
        return tuple(sorted([make_hashable(item) for item in obj]))

    if isinstance(obj, dict):
        hashable_dict = {}
        for k, v in obj.items():
            hashable_dict[k] = make_hashable(v)
        return tuple(sorted(hashable_dict))

    return obj
