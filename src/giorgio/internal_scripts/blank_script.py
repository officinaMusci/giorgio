#!/usr/bin/env python3
"""
Blank Script Template for Giorgio.

This template provides a basic structure for creating new automation scripts.
Customize as needed.
"""

from typing import Dict, Any
import os

from giorgio.giorgio import GiorgioApp


def get_config_schema() -> Dict[str, Dict[str, Any]]:
    """
    Return the main configuration schema for the script.
    For example, the script requires a folder path.
    """
    return {
        "folder": {
            "type": "string",
            "default": "./data",
            "label": "Folder Path"
        }
    }

def run(params: Dict[str, Any], app: GiorgioApp) -> None:
    """
    Execute the script using provided parameters.
    
    :param params: Main parameters from the configuration.
    :param app: The GiorgioApp instance, allowing dynamic GUI updates.
    """
    folder = params.get("folder")
    if not folder or not os.path.isdir(folder):
        print("Invalid folder path.")
        return

    print("Processing folder:", folder)
    
    # Schema for additional parameters adapted to the new format.
    extra_schema = {
        "file_choice": {
            "type": "string",
            "default": "",
            "label": "Choose a file from folder",
            "options": sorted(os.listdir(folder)),
            "multiple": False
        },
        "comment": {
            "type": "string",
            "default": "",
            "label": "Enter your comment"
        }
    }
    
    # Dynamically append extra fields and wait for user input.
    extra_params = app.get_additional_params("Extra Parameters", extra_schema)
    
    print("Script running with parameters:")
    print("Main parameter 'folder':", folder)
    print("Additional parameters:", extra_params)
