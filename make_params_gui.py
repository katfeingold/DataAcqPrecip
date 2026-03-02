import tkinter as tk
from tkinter import filedialog, messagebox
import os

# Default template comments/structure
HEADER = """# params.txt
# destination: where to save downloaded GRIB2 files
destination = {destination}

# in_file can be a full glob pattern or a directory. 
# this should match "destination
# If you give a directory only, the script will append 
# /MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz for user
in_file     = {in_file}

# Optional intermediate folder for output DSS
out_dir     = {out_dir}

# The final DSS filename (will be joined with out_dir )
out_file    = {out_file}

# The shapefile to clip to
shape_file  = {shape_file}

# DSS parts
DSSA        = {DSSA}
DSSB        = {DSSB}
DSSC        = {DSSC}
DSSF        = {DSSF}
"""

def browse_dir(entry_widget):
    path = filedialog.askdirectory()
    if path:
        # Escape backslashes for the params.txt format
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path.replace("\\", "\\\\"))

def browse_file(entry_widget, filetypes=None):
    path = filedialog.askopenfilename(filetypes=filetypes or [("All files", "*.*")])
    if path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path.replace("\\", "\\\\"))

def browse_out_file(entry_widget):
    path = filedialog.asksaveasfilename(
        defaultextension=".dss",
        filetypes=[("DSS files", "*.dss"), ("All files", "*.*")]
    )
    if path:
        # Only store the filename, since your script joins with out_dir
        filename = os.path.basename(path)
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filename)

def save_params(entries):
    values = {name: e.get().strip() for name, e in entries.items()}

    # Minimal validations (you can add more)
    required = ["destination", "in_file", "out_dir", "out_file", "shape_file"]
    missing = [r for r in required if not values[r]]
    if missing:
        messagebox.showerror(
            "Missing values",
            "Please fill in: " + ", ".join(missing)
        )
        return

    # Ask where to save params.txt
    save_path = filedialog.asksaveasfilename(
        initialfile="params.txt",
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not save_path:
        return

    # Fill template
    text = HEADER.format(**values)

    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("Success", f"params.txt created at:\n{save_path}")
    except Exception as ex:
        messagebox.showerror("Error", f"Could not save file:\n{ex}")

def main():
    root = tk.Tk()
    root.title("params.txt creator")

    # Field definitions: name, label, widget type
    fields = [
        ("destination", "Destination folder"),
        ("in_file", "Input folder / glob"),
        ("out_dir", "Output DSS folder"),
        ("out_file", "Output DSS filename"),
        ("shape_file", "Shapefile (.shp)"),
        ("DSSA", "DSSA part"),
        ("DSSB", "DSSB part"),
        ("DSSC", "DSSC part"),
        ("DSSF", "DSSF part"),
    ]

    entries = {}

    for i, (name, label) in enumerate(fields):
        tk.Label(root, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=3)
        e = tk.Entry(root, width=60)
        e.grid(row=i, column=1, padx=5, pady=3)
        entries[name] = e

        # Add browse buttons for paths
        if name in ("destination", "in_file", "out_dir"):
            tk.Button(root, text="Browse...", command=lambda w=e: browse_dir(w))\
              .grid(row=i, column=2, padx=5, pady=3)
        elif name == "shape_file":
            tk.Button(
                root,
                text="Browse...",
                command=lambda w=e: browse_file(w, filetypes=[("Shapefiles", "*.shp"), ("All files", "*.*")])
            ).grid(row=i, column=2, padx=5, pady=3)
        elif name == "out_file":
            tk.Button(root, text="Browse...", command=lambda w=e: browse_out_file(w))\
              .grid(row=i, column=2, padx=5, pady=3)

    # Set some example defaults (you can change/remove these)
    entries["destination"].insert(0, r"C:\\Temp\\RATTEMP")
    entries["in_file"].insert(0, r"C:\\Temp\\RATTEMP")
    entries["out_dir"].insert(0, r"C:\\Temp\\RATTEMP\\DSSOUT")
    entries["out_file"].insert(0, "test_config.dss")
    entries["shape_file"].insert(0, r"C:\\Projects\\...\\Subbasins_Reprojected.shp")
    entries["DSSA"].insert(0, "SHG")
    entries["DSSB"].insert(0, "MRMS")
    entries["DSSC"].insert(0, "Precip")
    entries["DSSF"].insert(0, "01H")

    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.grid(row=len(fields), column=0, columnspan=3, pady=10)

    tk.Button(btn_frame, text="Create params.txt",
              command=lambda: save_params(entries)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Quit", command=root.destroy).pack(side="left", padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()
