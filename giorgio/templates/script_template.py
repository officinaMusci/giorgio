from giorgio.execution_engine import Context, GiorgioCancellationError

CONFIG = {
    "name": "__SCRIPT_PATH__",
    "description": ""
}

PARAMS = { }


def run(context: Context):
    try:
        # Your script logic goes here
        print("Running the script...")
    
    except GiorgioCancellationError:
        print("Execution was cancelled by the user.")
