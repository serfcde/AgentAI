import json
import os

import yaml
from crewai.tools import tool


@tool("File Reader Tool")
def file_reader_tool(file_path: str) -> str:
    """
    Read TXT, JSON, and YAML files.
    Useful for reading workflow data,
    configuration files, and reports.
    """

    try:

        if not os.path.exists(file_path):
            return "File not found."

        file_extension = file_path.split(".")[-1]

        with open(file_path, encoding="utf-8") as file:

            if file_extension == "txt":
                return file.read()

            elif file_extension == "json":
                data = json.load(file)
                return json.dumps(data, indent=2)

            elif file_extension in ["yaml", "yml"]:
                data = yaml.safe_load(file)
                return yaml.dump(data, indent=2)

            else:
                return "Unsupported file format."

    except Exception as error:

        return f"File Reader Tool Error: {str(error)}"
