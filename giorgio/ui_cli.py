import sys
import questionary
from typing import Any, Dict, List

from .ui_renderer import UIRenderer
from .prompt import script_finder, prompt_for_params


class CLIUIRenderer(UIRenderer):
    """
    Command-line UI using questionary and stdout.
    """

    def list_scripts(self, scripts: List[str]) -> str:
        """
        Prompt the user to select a script from a list.
        
        :param scripts: List of script names to choose from.
        :type scripts: List[str]
        :return: The name of the selected script.
        :rtype: str
        """

        return script_finder(
            "Select a script to run:",
            choices=scripts,
            scripts_dir="scripts"
        ).ask()

    def prompt_params(
            self, schema: Dict[str, Dict[str, Any]], env: Dict[str, str]
        ) -> Dict[str, Any]:
        """
        Prompt the user for parameters based on a schema and environment
        variables.

        :param schema: The schema defining the parameters to prompt for.
        :type schema: Dict[str, Dict[str, Any]]
        :param env: The environment variables to use as defaults.
        :type env: Dict[str, str]
        :return: A dictionary of user-provided parameters.
        :rtype: Dict[str, Any]
        """

        return prompt_for_params(schema, env)

    def stream_output(self, text: str) -> None:
        """
        Stream output to the console in CLI mode.

        :param text: The text to output to the console.
        :type text: str
        :raises NotImplementedError: This method is not implemented for CLI mode.
        :return: None
        :rtype: None
        """

        sys.stdout.write(text)
        sys.stdout.flush()

    def wait_for_stop(self) -> None:
        """
        Wait for the user to stop the script execution.

        :raises GiorgioCancellationError: This method is designed to be interrupted by
        a keyboard interrupt (Ctrl+C) in CLI mode.
        :return: None
        :rtype: None
        """
        pass
