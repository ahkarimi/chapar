import json
import os
from pathlib import Path

def load_json_file(file_path):
    """
    Load and parse JSON file from the given path.

    Args:
        file_path (str): Path to the JSON file

    Returns:
        dict: Parsed JSON data
    """
    try:
        # Get the absolute path if a relative path is provided
        if not os.path.isabs(file_path):
            # Get the application root directory (assuming this file is in app/core)
            app_root = Path(__file__).parent.parent
            file_path = os.path.join(app_root, file_path)

        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Error loading JSON file {file_path}: {str(e)}")
