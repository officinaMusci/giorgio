#!/usr/bin/env python3
"""
Blank Script Template for Giorgio.

This template provides a basic structure for creating new automation scripts.
Customize as needed.
"""

from typing import Dict, Any
import os

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

def run(params: Dict[str, Any], app) -> None:
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
    
    # At some point, additional parameters are needed.
    # The developer creates a configuration dict for the extra parameters.
    extra_schema = {
        "file_choice": {
            "label": "Choose a file from folder",
            "widget": "listbox",
            "default": "",
            "options": sorted(os.listdir(folder))
        },
        "comment": {
            "label": "Enter your comment",
            "widget": "entry",
            "default": ""
        }
    }
    
    # Dynamically append extra fields and wait for user input.
    extra_params = app.get_additional_params("Dynamic Parameters", extra_schema)
    
    # Continue script execution using both main and additional parameters.
    print("Script running with parameters:")
    print("Main parameter 'folder':", folder)
    print("Additional parameters:", extra_params)
