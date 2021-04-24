import durations
from aws_hashicorp_packer_reaper.logger import log
from jsonschema.exceptions import ValidationError
from jsonschema import validators, Draft7Validator, FormatChecker, validators


schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "description": "of operations",
            "enum": ["stop", "terminate"],
        },
        "older_than": {
            "type": "string",
            "description": "period since launched",
            "format": "duration",
            "default": "2h",
        },
        "dry_run": {
            "type": "boolean",
            "description": "if you only want output",
            "default": True,
        },
        "tags": {
            "type": "array",
            "description": "to select EC2 instances with",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": [
        "mode",
        "older_than",
    ],
}


@FormatChecker.cls_checks("duration")
def duration_checker(value) -> bool:
    """
    checks whether the `value` is a valid duration.

    >>> duration_checker({})
    False

    >>> duration_checker(1.0)
    False

    >>> duration_checker("2h")
    True

    >>> duration_checker("hundred days")
    False
    """
    try:
        if isinstance(value, str):
            durations.Duration(value)
            return True
    except durations.exceptions.InvalidTokenError as e:
        pass
    return False


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(
        validator_class,
        {"properties": set_defaults},
    )

validator = extend_with_default(Draft7Validator)(schema, format_checker=FormatChecker())


def validate(request: dict) -> bool:
    """
    return True and completes the missing values if the dictionary matches the schema, otherwise False.
    >>> validate({"mode": "stoep"})
    False
    >>> validate({"mode": "stop", "older_than": "sdfsdfsf dagen"})
    False
    >>> x = {"mode": "stop"}
    >>> validate(x)
    True
    >>> print(x)
    {'mode': 'stop', 'older_than': '2h', 'dry_run': True}
    """
    try:
        validator.validate(request)
        return True
    except ValidationError as e:
        log.error("invalid request received: %s" % str(e.message))
        return False
