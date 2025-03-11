#!/usr/bin/env python3
"""
Giorgio - A lightweight micro-framework for script automation with a GUI.
"""

import os
import json
import importlib.util
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from typing import Dict, Any, Optional

CONFIG_FILE = 'config.json'
SCRIPTS_FOLDER = 'scripts'


class GiorgioApp:
    """
    Main application class for Giorgio.
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the Giorgio application.

        :param root: The root Tkinter window.
        """
        self.root = root
        self.root.title("Giorgio - Automation Butler")
        self.config_data = self.load_config()
        self.scripts = self.scan_scripts()
        self.current_script: Optional[str] = None
        self.script_module: Optional[Any] = None
        self.param_widgets: Dict[str, tk.Entry] = {}
        self.create_widgets()

    def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the CONFIG_FILE.

        :return: A dictionary with configuration data.
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Config Error",
                                     f"Error loading config file: {e}")
                return {}
        return {}

    def save_config(self) -> None:
        """
        Save the current configuration data to the CONFIG_FILE.
        """
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error",
                                 f"Error saving config file: {e}")

    def scan_scripts(self) -> Dict[str, str]:
        """
        Scan the SCRIPTS_FOLDER for available script files.

        :return: A dict mapping script names to their file paths.
        """
        scripts = {}
        if not os.path.exists(SCRIPTS_FOLDER):
            os.makedirs(SCRIPTS_FOLDER)
        for file in os.listdir(SCRIPTS_FOLDER):
            if file.endswith('.py'):
                script_name = file[:-3]
                scripts[script_name] = os.path.join(SCRIPTS_FOLDER, file)
        return scripts

    def create_widgets(self) -> None:
        """
        Create the main GUI widgets.
        """
        # Create main frames.
        self.left_frame = ttk.Frame(self.root, width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                              padx=5, pady=5)

        # List of available scripts.
        ttk.Label(self.left_frame, text="Available Scripts:").pack(
            anchor=tk.W)
        self.script_listbox = tk.Listbox(self.left_frame)
        self.script_listbox.pack(fill=tk.BOTH, expand=True)
        for script in self.scripts:
            self.script_listbox.insert(tk.END, script)
        self.script_listbox.bind('<<ListboxSelect>>', self.on_script_select)

        # Frame for script parameters form.
        self.form_frame = ttk.LabelFrame(self.right_frame,
                                         text="Script Parameters")
        self.form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Button to run the script.
        self.run_button = ttk.Button(self.right_frame, text="Run Script",
                                     command=self.run_script)
        self.run_button.pack(pady=5)

        # Output display area.
        self.output_text = scrolledtext.ScrolledText(self.right_frame, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Menu for editing configuration and viewing docs.
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuration", menu=config_menu)
        config_menu.add_command(label="Edit Config", command=self.edit_config)
        config_menu.add_command(label="Documentation",
                                command=self.show_documentation)

    def on_script_select(self, event: tk.Event) -> None:
        """
        Event handler when a script is selected from the listbox.

        :param event: Tkinter event.
        """
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            script_name = event.widget.get(index)
            self.current_script = script_name
            self.load_script(script_name)
            self.build_form()

    def load_script(self, script_name: str) -> None:
        """
        Dynamically load the selected script module.

        :param script_name: Name of the script to load.
        """
        script_path = self.scripts.get(script_name)
        if script_path:
            spec = importlib.util.spec_from_file_location(script_name,
                                                           script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            self.script_module = module
        else:
            self.script_module = None

    def build_form(self) -> None:
        """
        Build the parameter form dynamically based on the script's
        configuration schema.
        """
        # Clear the previous form.
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.param_widgets = {}
        schema: Dict[str, Any] = {}
        if self.script_module and hasattr(self.script_module,
                                           'get_config_schema'):
            try:
                schema = self.script_module.get_config_schema()
            except Exception as e:
                messagebox.showerror("Error", f"Error getting schema: {e}")
        if not schema:
            ttk.Label(self.form_frame,
                      text="No parameters required for this script.").pack()
            return

        row = 0
        # Retrieve stored configuration for this script, if available.
        stored_config: Dict[str, Any] = self.config_data.get(
            self.current_script, {})

        for key, props in schema.items():
            label_text = props.get("label", key)
            ttk.Label(self.form_frame, text=label_text).grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(self.form_frame)
            default_value = stored_config.get(key, props.get("default", ""))
            entry.insert(0, str(default_value))
            entry.grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
            self.param_widgets[key] = entry

            # If a description is provided in the schema, display it as a tooltip.
            desc = props.get("description", "")
            if desc:
                # Simple tooltip implementation: show description on focus.
                def on_focus_in(event, text=desc):
                    messagebox.showinfo("Parameter Info", text)
                entry.bind("<FocusIn>", on_focus_in)

            row += 1
        self.form_frame.columnconfigure(1, weight=1)

    def run_script(self) -> None:
        """
        Collect parameters from the form, update the configuration, and run
        the selected script in a separate thread.
        """
        if not self.script_module or not hasattr(self.script_module, 'run'):
            messagebox.showerror("Error",
                                 "The selected script does not have a 'run' "
                                 "function.")
            return
        params = {key: widget.get() 
                  for key, widget in self.param_widgets.items()}
        if self.current_script:
            self.config_data[self.current_script] = params
        self.save_config()
        self.output_text.delete(1.0, tk.END)
        thread = threading.Thread(target=self.execute_script, args=(params,))
        thread.start()

    def execute_script(self, params: Dict[str, Any]) -> None:
        """
        Execute the script's run function with provided parameters and
        display its output.

        :param params: Dictionary of parameters for the script.
        """
        try:
            import io, sys
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            self.script_module.run(params)  # type: ignore
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            self.output_text.insert(tk.END, output)
        except Exception as e:
            self.output_text.insert(tk.END,
                                    f"Error executing script: {e}")

    def edit_config(self) -> None:
        """
        Open a window to allow the user to edit the configuration in JSON
        format.
        """
        top = tk.Toplevel(self.root)
        top.title("Edit Configuration")
        text = scrolledtext.ScrolledText(top, width=60, height=20)
        text.pack(padx=10, pady=10)
        text.insert(tk.END, json.dumps(self.config_data, indent=4))

        def save_and_close() -> None:
            """
            Save the edited configuration and close the window.
            """
            try:
                new_config = json.loads(text.get(1.0, tk.END))
                self.config_data = new_config
                self.save_config()
                top.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid JSON: {e}")

        save_btn = ttk.Button(top, text="Save", command=save_and_close)
        save_btn.pack(pady=5)

    def show_documentation(self) -> None:
        """
        Open a window to display the project's README.md.
        """
        readme_path = 'README.md'
        if not os.path.exists(readme_path):
            messagebox.showinfo("Documentation", "README.md not found.")
            return

        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Error loading README.md: {e}")
            return

        doc_window = tk.Toplevel(self.root)
        doc_window.title("Documentation")
        text_area = scrolledtext.ScrolledText(doc_window, width=80, height=25)
        text_area.pack(padx=10, pady=10)
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)


def main() -> None:
    """
    Main function to start the Giorgio application.
    """
    root = tk.Tk()
    app = GiorgioApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
