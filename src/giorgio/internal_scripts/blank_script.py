#!/usr/bin/env python3
"""
Blank Script Template for Giorgio.

This template provides a basic structure for creating new scripts.
Customize the functions as needed.
"""

from typing import Dict, Any


def get_config_schema() -> Dict[str, Dict[str, Any]]:
    """
    Return the configuration schema for this script.

    :return: A dict defining parameters, their default values, and labels.
    """
    return {
        "description": {
            "type": "string",
            "default": "A blank script template.",
            "label": "Script Description",
            "description": "Describe what this script does."
        },
        "param1": {
            "type": "string",
            "default": "",
            "label": "Parameter 1",
            "description": "Enter the value for parameter 1."
        }
    }


def run(params: Dict[str, Any]) -> None:
    """
    Execute the script with provided parameters.

    :param params: Dictionary of parameters.
    """
    print("This is a blank script template. Please customize it.")
    print("Received parameters:")
    for key, value in params.items():
        print(f"{key}: {value}")
