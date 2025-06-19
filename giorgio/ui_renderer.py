from abc import ABC, abstractmethod
from typing import List, Dict, Any


class UIRenderer(ABC):
    """
    Abstract interface for script execution UIs.
    """

    @abstractmethod
    def list_scripts(self, scripts: List[str]) -> str:
        """
        Present a list of script names and return the selected one.
        """
        
        pass

    @abstractmethod
    def prompt_params(self, schema: Dict[str, Dict[str, Any]], env: Dict[str, str]) -> Dict[str, Any]:
        """
        Prompt the user for parameters defined in the schema.
        """
        pass

    @abstractmethod
    def stream_output(self, text: str) -> None:
        """
        Stream output text to the UI.
        """
        
        pass

    @abstractmethod
    def wait_for_stop(self) -> None:
        """
        Block or listen for user-initiated stop (e.g. Ctrl+C).
        """

        pass