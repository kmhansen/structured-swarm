from datetime import datetime
import inspect
from typing import get_type_hints
from pydantic import BaseModel, create_model
import openai


def debug_print(debug: bool, *args: str) -> None:
    if not debug:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = " ".join(map(str, args))
    print(f"\033[97m[\033[90m{timestamp}\033[97m]\033[90m {message}\033[0m")


def merge_fields(target, source):
    for key, value in source.items():
        if isinstance(value, str):
            target[key] += value
        elif value is not None and isinstance(value, dict):
            merge_fields(target[key], value)


def merge_chunk(final_response: dict, delta: dict) -> None:
    delta.pop("role", None)
    merge_fields(final_response, delta)

    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index")
        merge_fields(final_response["tool_calls"][index], tool_calls[0])


def function_to_json(func) -> dict:
    if get_type_hints(func) != {}:
        return structured_function_to_json(func)
    else:
        return unstructured_function_to_json(func)

def convert_structured_types(func, args: dict) -> None:
    if get_type_hints(func) == {}:
        return
    
    type_hints = get_type_hints(func)
    for arg_name, arg_value in args.items():
        if arg_name in type_hints:
            hint_type = type_hints[arg_name]
            if isinstance(hint_type, type) and issubclass(hint_type, BaseModel):
                args[arg_name] = hint_type.model_validate(arg_value)

def unstructured_function_to_json(func) -> dict:
    """
    Converts a Python function into a JSON-serializable dictionary
    that describes the function's signature, including its name,
    description, and parameters.

    Args:
        func: The function to be converted.

    Returns:
        A dictionary representing the function's signature in JSON format.
    """
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    try:
        signature = inspect.signature(func)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {func.__name__}: {str(e)}"
        )

    parameters = {}
    for param in signature.parameters.values():
        try:
            param_type = type_map.get(param.annotation, "string")
        except KeyError as e:
            raise KeyError(
                f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
            )
        parameters[param.name] = {"type": param_type}

    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }
    
def structured_function_to_json(func) -> dict:
    """
    Converts a Python function into a JSON-serializable dictionary
    that describes the function's signature, including its name,
    description, and parameters.
    
    The function is described in a way such that its parameters 
    correspond to Structured Outputs.

    Args:
        func: The function to be converted.

    Returns:
        A dictionary representing the function's signature in JSON format.
    """

    type_hints = get_type_hints(func)
    fields = {param: (type_hints[param], None) for param in type_hints}
    if "return" in fields:
        del fields["return"]
    func_model = create_model(
        func.__name__,
        **fields)

    func_model.__doc__ = func.__doc__ or ""

    result = openai.pydantic_function_tool(func_model)

    return result
