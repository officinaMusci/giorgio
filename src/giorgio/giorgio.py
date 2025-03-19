#!/usr/bin/env python3
"""
Giorgio - A lightweight micro-framework for script automation with a GUI.
"""

import importlib.util
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, List

def create_grouped_form(
    container: tk.Frame,
    grouped_schema: Dict[str, Dict[str, Any]],
    options: Dict[str, list] = None
) -> Dict[str, Dict[str, tk.Widget]]:
    """
    Create grouped input fields in the given container based on a grouped schema.
    
    Each key in grouped_schema is a section name mapping to a dict describing fields.
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

def append_additional_fields(
    container: tk.Frame, group_name: str, schema: Dict[str, Any],
    options: Dict[str, list] = None
) -> Dict[str, tk.Widget]:
    """
    Append additional parameter fields to the given container.
    
    :return: Dict mapping field names to widgets for the new group.
    """
    grouped = {group_name: schema}
    widgets = create_grouped_form(container, grouped, options=options)
    return widgets[group_name]

def list_available_scripts(scripts_path: str) -> List[str]:
    """
    List available Python script files in the given directory (excluding __init__.py).
    """
    scripts = []
    try:
        for file in os.listdir(scripts_path):
            if file.endswith(".py") and file != "__init__.py":
                scripts.append(file[:-3])
    except Exception:
        pass
    return sorted(scripts)

class GiorgioApp(tk.Tk):
    """
    Main application class for Giorgio.
    """
    def __init__(self) -> None:
        super().__init__()
        self.title("Giorgio - Automation Butler")
        self.geometry("800x600")
        
        # Main container divided into two columns: sidebar and main panel.
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.container.columnconfigure(1, weight=1)
        
        # Sidebar: list available scripts from the project's "scripts" folder.
        self.sidebar = ttk.Frame(self.container, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        ttk.Label(self.sidebar, text="Available Scripts", font=("TkDefaultFont", 10, "bold")).pack(pady=5)
        self.script_listbox = tk.Listbox(self.sidebar)
        self.script_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.load_script_list()
        
        # Main panel
        self.main_panel = ttk.Frame(self.container)
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # Main Parameters
        self.config_frame = ttk.LabelFrame(self.main_panel, text="Main Parameters")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(self.config_frame, text="Folder:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.folder_entry = ttk.Entry(self.config_frame)
        self.folder_entry.insert(0, "./data")
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.config_frame.columnconfigure(1, weight=1)
        
        # Additional Parameters section (created in place but hidden)
        self.additional_frame = ttk.LabelFrame(self.main_panel, text="Additional Parameters")
        self.additional_frame.pack(fill=tk.X, padx=5, pady=5)
        self.additional_frame.pack_forget()
        
        # Reordering the display order:
        # First, the console below the sections
        self.output_text = scrolledtext.ScrolledText(self.main_panel, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Then, the Run Script button at the bottom
        self.run_btn = ttk.Button(self.main_panel, text="Run Script", command=self.on_run)
        self.run_btn.pack(pady=5)
        
        # Variables for additional input
        self._continue_var = tk.BooleanVar(value=False)
        self._waiting_for_additional = False
        
        # Storage of additional widgets by group
        self.additional_widgets: Dict[str, Dict[str, tk.Widget]] = {}

    def load_script_list(self) -> None:
        """
        Load the list of available scripts from the project's "scripts" folder.
        """
        scripts_path = os.path.join(os.getcwd(), "scripts")
        scripts = list_available_scripts(scripts_path)
        self.script_listbox.delete(0, tk.END)
        for script in scripts:
            self.script_listbox.insert(tk.END, script)
        if scripts:
            self.script_listbox.select_set(0)

    def on_run(self) -> None:
        """
        Handler for the Run/Continue button.
        """
        if self._waiting_for_additional:
            self._continue_var.set(True)
        else:
            self.execute_script()

    def show_additional_frame(self) -> None:
        """
        Display the Additional Parameters section if it is hidden.
        """
        if not self.additional_frame.winfo_ismapped():
            self.additional_frame.pack(fill=tk.X, padx=5, pady=5, before=self.output_text)

    def hide_additional_frame(self) -> None:
        """
        Clear and hide the Additional Parameters section.
        """
        for child in self.additional_frame.winfo_children():
            child.destroy()
        self.additional_frame.pack_forget()
        self.additional_widgets = {}

    def get_additional_params(self, group_name: str, schema: Dict[str, Any],
                              options: Dict[str, list] = None) -> Dict[str, Any]:
        """
        Add additional fields in the Additional Parameters section, wait for input, and return the values.
        """
        self.show_additional_frame()
        widgets = append_additional_fields(self.additional_frame, group_name, schema, options)
        self.additional_widgets[group_name] = widgets
        
        self._waiting_for_additional = True
        self.run_btn.config(text="Continue")
        self._continue_var.set(False)
        self.wait_variable(self._continue_var)
        group_values = get_grouped_values({group_name: widgets})[group_name]
        self._waiting_for_additional = False
        self.run_btn.config(text="Run Script")
        return group_values

    def execute_script(self) -> None:
        """
        Load and execute the selected script from the project's "scripts" folder, pass the main parameters,
        display the results in the console, and hide the Additional Parameters section.
        """
        # Clear the console and hide Additional Parameters at the beginning of a new run.
        self.output_text.delete("1.0", tk.END)
        additional_values = get_grouped_values(self.additional_widgets)
        self.hide_additional_frame()

        folder = self.folder_entry.get()
        selection = self.script_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No script selected.")
            return
        script_name = self.script_listbox.get(selection[0])
        
        # Absolute path to the project's "scripts" folder (using os.getcwd())
        scripts_path = os.path.join(os.getcwd(), "scripts")
        script_file = os.path.join(scripts_path, f"{script_name}.py")
        
        try:
            spec = importlib.util.spec_from_file_location(script_name, script_file)
            script_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(script_module)  # type: ignore
        except Exception as e:
            messagebox.showerror("Error", f"Error loading script: {e}")
            return
        
        main_params = {"folder": folder}
        script_module.run(main_params, self)
        
        output = f"Main parameter 'folder': {folder}\nAdditional parameters:\n"
        for group, values in additional_values.items():
            output += f"Section: {group}\n"
            for key, value in values.items():
                output += f"  {key}: {value}\n"
        self.output_text.insert(tk.END, output)

def main() -> None:
    """Entry point to launch the Giorgio GUI."""
    app = GiorgioApp()
    app.mainloop()

if __name__ == "__main__":
    main()
