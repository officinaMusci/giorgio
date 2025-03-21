#!/usr/bin/env python3
"""
Giorgio - A lightweight micro-framework for script automation with a GUI.
"""

import importlib.util
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, List
from pathlib import Path


def create_grouped_form(
    container: tk.Frame,
    grouped_schema: Dict[str, Dict[str, Any]],
    options: Dict[str, list] = None
) -> Dict[str, Dict[str, tk.Widget]]:
    """
    Create grouped input fields in the given container based on a grouped schema.
    """
    all_widgets: Dict[str, Dict[str, tk.Widget]] = {}
    for group_name, schema in grouped_schema.items():
        group_frame = ttk.LabelFrame(container, text=group_name)
        group_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        widgets: Dict[str, tk.Widget] = {}
        for row, (key, config) in enumerate(schema.items()):
            label_text = config.get("label", key)
            ttk.Label(group_frame, text=label_text).grid(
                row=row, column=0, sticky="w", padx=5, pady=5
            )
            data_type = config.get("type", "string")
            if "options" in config:
                widget = tk.Listbox(
                    group_frame,
                    selectmode=tk.MULTIPLE if config.get("multiple", False) else tk.BROWSE,
                    height=6,
                    exportselection=False
                )
                opts = options.get(key) if options and key in options else config.get("options", [])
                for item in opts:
                    widget.insert(tk.END, item)
            elif data_type == "boolean":
                var = tk.BooleanVar(value=config.get("default", False))
                widget = ttk.Checkbutton(group_frame, variable=var)
                widget.var = var
            else:
                widget = ttk.Entry(group_frame)
                widget.insert(0, str(config.get("default", "")))
            widget.data_type = data_type
            widget.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
            widgets[key] = widget
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
                group_result[key] = (
                    widget.get(indices[0]) if widget.cget("selectmode") == "browse" and indices else
                    [widget.get(i) for i in indices]
                )
            elif isinstance(widget, ttk.Checkbutton) and hasattr(widget, "var"):
                group_result[key] = widget.var.get()
            elif isinstance(widget, ttk.Entry):
                val = widget.get()
                dt = getattr(widget, "data_type", "string")
                if dt == "integer":
                    group_result[key] = int(val) if val.isdigit() else val
                elif dt == "boolean":
                    group_result[key] = val.lower() in ("true", "1", "yes")
                elif dt == "path":
                    group_result[key] = Path(val)
                else:
                    group_result[key] = val
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
    """
    grouped = {group_name: schema}
    widgets = create_grouped_form(container, grouped, options=options)
    return widgets[group_name]


def list_available_scripts(scripts_path: str) -> List[str]:
    """
    List available Python script files in the given directory (excluding __init__.py).
    """
    try:
        return sorted(
            file[:-3] for file in os.listdir(scripts_path)
            if file.endswith(".py") and file != "__init__.py"
        )
    except Exception:
        return []


class GiorgioApp(tk.Tk):
    """
    Main application class for Giorgio.
    """
    def __init__(self) -> None:
        super().__init__()
        self.title("Giorgio - Automation Butler")
        self.geometry("800x600")
        
        # Create a canvas and a scrollbar to make the content scrollable
        self.canvas = tk.Canvas(self)
        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.v_scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Main container placed inside the canvas
        self.container = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.container, anchor="nw")
        self.container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Sidebar: list available scripts.
        self.sidebar = ttk.Frame(self.container, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        ttk.Label(self.sidebar, text="Available Scripts", font=("TkDefaultFont", 10, "bold")).pack(pady=5)
        self.script_listbox = tk.Listbox(self.sidebar)
        self.script_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.script_listbox.bind("<<ListboxSelect>>", lambda e: self.on_script_selected())
        
        # Main panel
        self.main_panel = ttk.Frame(self.container)
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # Main Parameters (will be generated dynamically)
        self.config_frame = ttk.LabelFrame(self.main_panel, text="Main Parameters")
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Additional Parameters section (hidden by default)
        self.additional_frame = ttk.LabelFrame(self.main_panel, text="Additional Parameters")
        self.additional_frame.pack(fill=tk.X, padx=5, pady=5)
        self.additional_frame.pack_forget()
        
        # Console and Run Script button.
        self.output_text = scrolledtext.ScrolledText(self.main_panel, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.run_btn = ttk.Button(self.main_panel, text="Run Script", command=self.on_run)
        self.run_btn.pack(pady=5)
        
        # Redirect stdout and stderr to the console widget.
        import sys
        class TextRedirector:
            def __init__(self, widget):
                self.widget = widget
            def write(self, s):
                self.widget.insert(tk.END, s)
                self.widget.see(tk.END)
            def flush(self):
                pass
        sys.stdout = TextRedirector(self.output_text)
        sys.stderr = TextRedirector(self.output_text)
        
        # Variables for additional inputs.
        self._continue_var = tk.BooleanVar(value=False)
        self._waiting_for_additional = False
        
        # Storage of additional widgets and main parameters.
        self.additional_widgets: Dict[str, Dict[str, tk.Widget]] = {}
        self.main_widgets: Dict[str, tk.Widget] = {}
        # Attribute to store the currently selected script.
        self.current_script = None
        self._disable_script_selection = False
        self._last_listbox_focus = False
        self.script_listbox.bind("<FocusIn>", lambda e: self._set_listbox_focus(True))
        self.script_listbox.bind("<FocusOut>", lambda e: self._set_listbox_focus(False))
        self._last_selected_script_index = None
        
        # Now load the script list and update UI if a script is selected.
        self.load_script_list()
        if self.script_listbox.curselection():
            self.on_script_selected()

    def _set_listbox_focus(self, focused: bool) -> None:
        """
        Updates the focus state of the Listbox.
        """
        self._last_listbox_focus = focused

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

    def on_script_selected(self) -> None:
        """
        Load the schema of the selected script and update the UI for main parameters.
        Does not reload the UI if the selected script is the same as the previous one.
        """
        if self._disable_script_selection or not self._last_listbox_focus:  # Check if selection is temporarily disabled or if the Listbox does not have focus
            return
        selection = self.script_listbox.curselection()
        if not selection:
            self.script_listbox.select_set(0)
            selection = self.script_listbox.curselection()
        self._last_selected_script_index = selection[0]  # Store the index of the selected script
        script_name = self.script_listbox.get(selection[0])
        if self.current_script == script_name:
            return
        self.current_script = script_name
        scripts_path = os.path.join(os.getcwd(), "scripts")
        script_file = os.path.join(scripts_path, f"{script_name}.py")
        try:
            spec = importlib.util.spec_from_file_location(script_name, script_file)
            script_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(script_module)  # type: ignore
            config_schema = script_module.get_config_schema()
            self.update_main_params_ui(config_schema)
        except Exception as e:
            messagebox.showerror("Error", f"Error loading script for UI update: {e}")

    def restore_script_selection(self) -> None:
        """
        Restore the script selection in the Listbox if it was lost.
        """
        if self._last_selected_script_index is not None:
            self._disable_script_selection = True  # Temporarily disable the event
            self.script_listbox.select_clear(0, tk.END)
            self.script_listbox.select_set(self._last_selected_script_index)
            self._disable_script_selection = False  # Re-enable the event

    def update_main_params_ui(self, config_schema: Dict[str, Dict[str, Any]]) -> None:
        """
        Rebuild the UI for main parameters based on the given schema.
        The schema is expected in a flat format, here wrapped in a 'Main Parameters' group.
        """
        self.restore_script_selection()  # Restore selection after UI update
        # Clear existing UI.
        for child in self.config_frame.winfo_children():
            child.destroy()
        grouped_schema = {"Main Parameters": config_schema}
        widgets = create_grouped_form(self.config_frame, grouped_schema)
        self.main_widgets = widgets["Main Parameters"]
        # Adjust container configuration.
        self.config_frame.columnconfigure(1, weight=1)

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

    def get_additional_params(self, title: str, schema: Dict[str, Any], options: Dict[str, list] = None) -> Dict[str, Any]:
        """
        Add additional fields in the Additional Parameters section using the same schema format as Main Parameters,
        wait for input, and return the values.
        """
        self.restore_script_selection()  # Restore selection before adding additional parameters
        self.show_additional_frame()
        grouped_schema = { title: schema }
        widgets = create_grouped_form(self.additional_frame, grouped_schema, options)
        self.additional_widgets[title] = widgets[title]
        
        self._waiting_for_additional = True
        self.run_btn.config(text="Continue")
        self._continue_var.set(False)
        self.wait_variable(self._continue_var)
        group_values = get_grouped_values({ title: widgets[title] })[title]
        self._waiting_for_additional = False
        self.run_btn.config(text="Run Script")
        return group_values

    def execute_script(self) -> None:
        """
        Load and execute the selected script from the project's "scripts" folder, pass the main parameters,
        display the results in the console, and hide the Additional Parameters section.
        """
        self.restore_script_selection()  # Restore selection before executing the script
        self._disable_script_selection = True  # Temporarily disable selection
        try:
            # Do not clear the console to allow persistence of all messages.
            # self.output_text.delete("1.0", tk.END)
            additional_values = get_grouped_values(self.additional_widgets)
            self.hide_additional_frame()

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
            
            # Retrieve the script's configuration schema.
            config_schema = script_module.get_config_schema()
            # Retrieve the values entered in the widgets of the "Main Parameters" block,
            # with type conversion via get_grouped_values.
            main_values = get_grouped_values({"Main Parameters": self.main_widgets})["Main Parameters"]
            # Merge with the schema's default value
            main_params = {}
            for key, conf in config_schema.items():
                main_params[key] = main_values.get(key, conf.get("default", ""))
            
            # Merge with any additional values.
            additional_flat = {}
            for group_values in additional_values.values():
                additional_flat.update(group_values)
            main_params.update(additional_flat)
            
            script_module.run(main_params, self)
            
            output = "Main parameters:\n"
            for key, value in main_params.items():
                output += f"  {key}: {value}\n"
            self.output_text.insert(tk.END, output)
        finally:
            self._disable_script_selection = False  # Re-enable selection

def main() -> None:
    """Entry point to launch the Giorgio GUI."""
    app = GiorgioApp()
    app.mainloop()

if __name__ == "__main__":
    main()
