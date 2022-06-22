import yaml
import json
import datetime
import base64

def load_yaml(filepath):
    with open(filepath) as fi:
        return yaml.safe_load(fi)


def save_json(obj, filepath):
    obj = make_json_serializable(obj)
    with open(filepath, "w") as fo:
        json.dump(obj, fo, sort_keys=True, indent=4)


def make_json_serializable(obj):
    if type(obj) is dict:
        for k in obj:
            obj[k] = make_json_serializable(obj[k])
    elif type(obj) is list or type(obj) is tuple:
        obj = [make_json_serializable(x) for x in obj]
    elif type(obj) is datetime.datetime:
        obj = str(obj)
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode()

    return obj

def now_datetime():
    return datetime.datetime.now()
