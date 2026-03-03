# -*- coding: utf-8 -*-
"""
Simple Tkinter GUI to create or edit params_qpf.txt
for the WPC QPF + GridReader workflow.
"""

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Name/location of the params file (same folder as this script)
SCRIPT_DIR = Path(__file__).resolve().parent
PARAMS_PATH = SCRIPT_DIR / "params_qpf.txt"


# --------------------------------------------
# sets default values if the file missing
# --------------------------------------------
DEFAULT_PARAMS = {
    "destination": r"C:\\Temp\\QPF",
    "in_file":     r"C:\\Temp\\QPF",
    "out_dir":     r"C:\\Temp\\QPF\\DSSOUT",
    "out_file":    "qpf_latest.dss",
    "shape_file":  r"C:\\Projects\\...\\Subbasins_Reprojected.shp",
    "DSSA":        "SHG",
    "DSSB":        "QPF",
    "DSSC":        "Forecast",
    "DSSF":        "06H-QPF",
}


def load_params() -> dict:
    """
    Read params_qpf.txt if it exists.
    Returns a dict with any found values, defaulting missing keys.
    """
    params = DEFAULT_PARAMS.copy()

    if not PARAMS_PATH.exists():
        return params

    with open(PARAMS_PATH, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            params[key.strip()] = val.strip()

    return params


def save_params(params: dict):
    """
    Write parameters back out to params_qpf.txt
    in the simple 'key = value' format.
    """
    lines = [
        "# params_qpf.txt",
        "# Configuration for WPC QPF + GridReader",
        "",
    ]
    for key in [
        "destination",
        "in_file",
        "out_dir",
        "out_file",
        "shape_file",
        "DSSA",
        "DSSB",
        "DSSC",
        "DSSF",
    ]:
        val = params.get(key, "")
        lines.append(f"{key} = {val}")
    lines.append("")  # final newline

    with open(PARAMS_PATH, "w") as f:
        f.write("\n".join(lines))


class ParamsEditor(tk.Tk):
    """
    Small Tkinter window with entries for each param,
    plus browse buttons for folder/file paths.
    """

    def __init__(self):
        super().__init__()

        self.title("Edit params_qpf.txt")
        self.resizable(False, False)

        # Slight padding
        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky="nsew")

        # Load existing or default params
        self.params = load_params()

        # Store Entry widgets keyed by param name
        self.entries = {}

        # Row counter for the grid layout
        row = 0

        # Helper to add a labeled entry and optional browse button
        def add_row(label_text, key, browse_type=None):
            nonlocal row

            ttk.Label(main, text=label_text).grid(row=row, column=0, sticky="e", padx=(0, 5), pady=2)

            entry = ttk.Entry(main, width=60)
            entry.grid(row=row, column=1, sticky="w", pady=2)
            entry.insert(0, self.params.get(key, ""))

            self.entries[key] = entry

            if browse_type is not None:
                def do_browse():
                    if browse_type == "dir":
                        path = filedialog.askdirectory(title=f"Select {label_text}")
                    elif browse_type == "file":
                        path = filedialog.askopenfilename(title=f"Select {label_text}")
                    else:
                        path = None

                    if path:
                        # Replace single backslashes with doubled backslashes
                        # to match the style used in the params file.
                        norm = path.replace("\\", "\\\\")
                        entry.delete(0, tk.END)
                        entry.insert(0, norm)

                btn = ttk.Button(main, text="Browse...", command=do_browse)
                btn.grid(row=row, column=2, sticky="w", padx=(5, 0), pady=2)

            row += 1

        # --------------------------------------------
        # Add form fields 
        # --------------------------------------------
        add_row("Destination folder", "destination", browse_type="dir")
        add_row("Input folder ", "in_file", browse_type="dir")
        add_row("Output DSS folder", "out_dir", browse_type="dir")
        add_row("Output DSS filename", "out_file", browse_type=None)
        add_row("Shapefile path", "shape_file", browse_type="file")
        add_row("DSS A part", "DSSA", browse_type=None)
        add_row("DSS B part", "DSSB", browse_type=None)
        add_row("DSS C part", "DSSC", browse_type=None)
        add_row("DSS F part", "DSSF", browse_type=None)

        # ----------------------------------------------
        # loosen up my buttons 
        # -----------------------------------------------
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(10, 0), sticky="e")

        save_btn = ttk.Button(btn_frame, text="Save", command=self.on_save)
        save_btn.grid(row=0, column=0, padx=(0, 5))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.grid(row=0, column=1)

    def on_save(self):
        """
        Collect values from the form, validate minimally,
        then write params_qpf.txt and close.
        """
        new_params = {}
        for key, entry in self.entries.items():
            new_params[key] = entry.get().strip()

        # ----------------------------------------------
        # insanity checks
        # --------------------------------------------- 

        if not new_params["destination"]:
            messagebox.showerror("Error", "Destination cannot be empty.")
            return
        if not new_params["out_file"]:
            messagebox.showerror("Error", "Output DSS filename cannot be empty.")
            return

        try:
            save_params(new_params)
            messagebox.showinfo("Saved", f"Parameters saved to:\n{PARAMS_PATH}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save params:\n{e}")


def main():
    app = ParamsEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
