#!/usr/bin/env python3
"""
Giorgio - A lightweight micro-framework for script automation with a GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any

def create_grouped_form(
    container: tk.Frame,
    grouped_schema: Dict[str, Dict[str, Any]],
    options: Dict[str, list] = None
) -> Dict[str, Dict[str, tk.Widget]]:
    """
    Create grouped input fields in the given container based on a grouped schema.
    
    :param container: Parent Tkinter frame.
    :param grouped_schema: Dict where each key is a section name and its value is a dict of field configurations.
    :param options: Optional dict providing options for fields (e.g. for listbox).
    :return: Dict mapping section names to a dict of field widgets.
    """
    all_widgets: Dict[str, Dict[str, tk.Widget]] = {}
    for group_name, schema in grouped_schema.items():
        group_frame = ttk.LabelFrame(container, text=group_name)
        group_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        widgets: Dict[str, tk.Widget] = {}
        row = 0
        for key, config in schema.items():
            label_text = config.get("label", key)
            ttk.Label(group_frame, text=label_text).grid(
                row=row, column=0, sticky="w", padx=5, pady=5
            )
            widget_type = config.get("widget", "entry")
            if widget_type == "entry":
                entry = ttk.Entry(group_frame)
                default_value = config.get("default", "")
                entry.insert(0, str(default_value))
                entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
                widgets[key] = entry
            elif widget_type == "listbox":
                lb = tk.Listbox(group_frame, selectmode=tk.MULTIPLE, height=6)
                opts = options.get(key) if options and key in options else config.get("options", [])
                for item in opts:
                    lb.insert(tk.END, item)
                lb.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
                widgets[key] = lb
            row += 1
        group_frame.columnconfigure(1, weight=1)
        all_widgets[group_name] = widgets
    return all_widgets

def get_grouped_values(
    widgets_grouped: Dict[str, Dict[str, tk.Widget]]
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve values from grouped input widgets.
    
    :param widgets_grouped: Dict mapping section names to field widgets.
    :return: Dict mapping section names to user-entered values.
    """
    results: Dict[str, Dict[str, Any]] = {}
    for group, widgets in widgets_grouped.items():
        group_result = {}
        for key, widget in widgets.items():
            if isinstance(widget, tk.Listbox):
                indices = widget.curselection()
                group_result[key] = [widget.get(i) for i in indices]
            else:
                group_result[key] = widget.get()
        results[group] = group_result
    return results

class GiorgioApp(tk.Tk):
    """
    Main application class for Giorgio.
    """
    def __init__(self) -> None:
        super().__init__()
        self.title("Giorgio - Automation Butler")
        self.geometry("600x600")
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main parameters section
        self.config_frame = ttk.LabelFrame(self.main_frame, text="Main Parameters")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(self.config_frame, text="Folder:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.folder_entry = ttk.Entry(self.config_frame)
        self.folder_entry.insert(0, "./data")
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.config_frame.columnconfigure(1, weight=1)
        
        # Additional parameters section (initially empty)
        self.additional_frame = ttk.LabelFrame(self.main_frame, text="Additional Parameters")
        self.additional_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Button to run the script (or continue when waiting for additional input)
        self.run_btn = ttk.Button(self.main_frame, text="Run Script", command=self.on_run)
        self.run_btn.pack(pady=5)
        
        # Output area to display results
        self.output_text = scrolledtext.ScrolledText(self.main_frame, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Variable for waiting on user input for additional parameters
        self._continue_var = tk.BooleanVar(value=False)
        
        # Dictionary to store additional field groups (by group name)
        self.additional_widgets: Dict[str, Dict[str, tk.Widget]] = {}

    def on_run(self) -> None:
        """
        Handler for the Run/Continue button.
        If the app is waiting for additional input, it releases the wait.
        Otherwise, it executes the script.
        """
        if not self._continue_var.get():
            self._continue_var.set(True)
        else:
            self.execute_script()
    
    def get_additional_params(self, group_name: str, schema: Dict[str, Any],
                              options: Dict[str, list] = None) -> Dict[str, Any]:
        """
        Append additional fields in a new group, wait until the user fills them in,
        and then return the values.
        
        :param group_name: Title for the new group.
        :param schema: Dict describing the fields.
        :param options: Optional dict for field options.
        :return: Dict with values from the new group.
        """
        # Append a new group of fields
        widgets = self.append_dynamic_fields(group_name, schema, options)
        # Change button label to "Continue" and reset the wait variable
        self.run_btn.config(text="Continue")
        self._continue_var.set(False)
        self.wait_variable(self._continue_var)
        # Retrieve and return the values from this group
        group_values = get_grouped_values({group_name: widgets})[group_name]
        self.run_btn.config(text="Run Script")
        return group_values

    def append_dynamic_fields(self, group_name: str, schema: Dict[str, Any],
                              options: Dict[str, list] = None) -> Dict[str, tk.Widget]:
        """
        Append additional parameter fields to the additional_frame.
        
        :param group_name: Title of the new group.
        :param schema: Dict describing the fields.
        :param options: Optional dict providing options.
        :return: Dict mapping field keys to widgets for this group.
        """
        grouped = {group_name: schema}
        widgets = create_grouped_form(self.additional_frame, grouped, options=options)
        self.additional_widgets[group_name] = widgets[group_name]
        return widgets[group_name]

    def get_all_additional_values(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all additional parameters from all groups.
        """
        return get_grouped_values(self.additional_widgets)

    def execute_script(self) -> None:
        """
        Execute the script by collecting main and additional parameters,
        then display the result.
        """
        folder = self.folder_entry.get()
        all_additional = get_grouped_values(self.additional_widgets)
        output = f"Main parameter 'folder': {folder}\nAdditional parameters:\n"
        for group, values in all_additional.items():
            output += f"Section: {group}\n"
            for key, value in values.items():
                output += f"  {key}: {value}\n"
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, output)

if __name__ == "__main__":
    app = GiorgioApp()
    app.mainloop()
