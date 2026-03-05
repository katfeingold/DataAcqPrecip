# -*- coding: utf-8 -*-
# ----------------------------------------------------------------
# What it Does: Download MRMS QPE files.
# Author (so you know who to yell at) Kat Feingold
# Last updated: 
# 3/4/2026 - creation
# 3/4/2026 - fixed the dialog box
# 3/4/2026 - added simple progress bar per file
# 
# -----------------------------------------------------------------


import os
import sys
from datetime import datetime, timedelta


import nest_asyncio
nest_asyncio.apply()


import asyncio
import aiohttp
import async_timeout


import tkinter as tk
from tkinter import ttk, messagebox, filedialog



#-------------------------------------------------------------------------------
# ASYNC Diwnload stuff
#-------------------------------------------------------------------------------
# These will be set before starting downloads
_progress_root = None
_progress_var = None
_progress_label = None
_progress_total = 0



def create_progress_window(total_files: int):
    """
    Create a small Tk window with a determinate progress bar showing
    how many files have been downloaded out of total_files.
    """
    global _progress_root, _progress_var, _progress_label, _progress_total
    _progress_total = total_files

    _progress_root = tk.Tk()
    _progress_root.title("MRMS Download Progress")
    _progress_root.resizable(False, False)

    frame = ttk.Frame(_progress_root, padding=10)
    frame.grid(row=0, column=0, sticky="nsew")

    _progress_var = tk.IntVar(value=0)

    ttk.Label(frame, text="Downloading MRMS files...").grid(
        row=0, column=0, sticky="w"
    )

    bar = ttk.Progressbar(
        frame,
        orient="horizontal",
        mode="determinate",
        maximum=total_files,
        variable=_progress_var,
        length=300,
    )
    bar.grid(row=1, column=0, pady=(5, 5))

    _progress_label = ttk.Label(frame, text=f"0 of {total_files} files")
    _progress_label.grid(row=2, column=0, sticky="w")

    # Center the window a bit
    _progress_root.update_idletasks()
    w = _progress_root.winfo_width()
    h = _progress_root.winfo_height()
    sw = _progress_root.winfo_screenwidth()
    sh = _progress_root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    _progress_root.geometry(f"+{x}+{y}")
    _progress_root.attributes("-topmost", True)
    _progress_root.lift()

    # Show initial state
    _progress_root.update()



def update_progress_window():
    """
    Increment the file counter and refresh the progress window.
    """
    global _progress_root, _progress_var, _progress_label, _progress_total
    if _progress_root is None:
        return

    current = _progress_var.get() + 1
    _progress_var.set(current)
    if _progress_label is not None:
        _progress_label.config(text=f"{current} of {_progress_total} files")
    _progress_root.update_idletasks()



def close_progress_window():
    """
    Close and destroy the progress window if it exists.
    """
    global _progress_root
    if _progress_root is not None:
        _progress_root.destroy()
        _progress_root = None



async def download_coroutine(url, session, destination, saved_files):
    async with async_timeout.timeout(1200):
        async with session.get(url) as response:
            if response.status == 200:
                fp = os.path.join(destination, os.path.basename(url))
                tmp_fp = fp + ".part"
                with open(tmp_fp, 'wb') as f_handle:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f_handle.write(chunk)
                os.replace(tmp_fp, fp)  # overwrite if exists
                saved_files.append(fp)
                # Update progress bar for each completed file
                update_progress_window()
            else:
                print("FAILED:", url)
            return await response.release()



async def main_async(url_list, destination):
    saved_files = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            download_coroutine(u, session, destination, saved_files)
            for u in url_list
        ]
        await asyncio.gather(*tasks)
    return saved_files



#-------------------------------------------------------------------------------------------
# Use TKINTER Dialog to get/input dates ( yeah its probably not great but its my first time)
#-------------------------------------------------------------------------------------------
def ask_date_range():
    """
    Show modal dialog.
    Returns (start_datetime, end_datetime) or None if cancelled.
    """
    root = tk.Tk()
    root.title("Select MRMS Date Range")
    root.resizable(False, False)

    root.geometry("+200+200")

    mode_var = tk.StringVar(value="custom")  # "custom" or "lookback"

    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")

    # ----------------------------------------------- 
    # Radio buttons because who doesn't love those 
    # -------------------------------------------------
    rb_custom = ttk.Radiobutton(
        frm, text="Custom range (DD-MMM-YYYY hh:mm)",
        variable=mode_var, value="custom"
    )
    rb_custom.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

    rb_lookback = ttk.Radiobutton(
        frm, text="Lookback (days from now)",
        variable=mode_var, value="lookback"
    )
    rb_lookback.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 5))

    ttk.Label(frm, text="Start:").grid(row=1, column=0, sticky="e")
    start_entry = ttk.Entry(frm, width=25)
    start_entry.grid(row=1, column=1, sticky="w")

    ttk.Label(frm, text="End:").grid(row=2, column=0, sticky="e")
    end_entry = ttk.Entry(frm, width=25)
    end_entry.grid(row=2, column=1, sticky="w")

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    start_entry.insert(0, yesterday.strftime("%d-%b-%Y 00:00"))
    end_entry.insert(0, today.strftime("%d-%b-%Y 00:00"))

    ttk.Label(frm, text="Days to look back:").grid(row=4, column=0, sticky="e")
    lookback_entry = ttk.Entry(frm, width=10)
    lookback_entry.grid(row=4, column=1, sticky="w")
    lookback_entry.insert(0, "1")

    result = {"start": None, "end": None}

    def on_save():
        try:
            if mode_var.get() == "custom":
                fmt = "%d-%b-%Y %H:%M"  # Needs to be DD-MMM-YYYY hh:mm Masks gotta love them
                start_str = start_entry.get().strip()
                end_str = end_entry.get().strip()
                start_dt = datetime.strptime(start_str, fmt)
                end_dt = datetime.strptime(end_str, fmt)
            else:
                days_str = lookback_entry.get().strip()
                days = int(days_str)
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=days)

                start_dt = start_dt.replace(minute=0, second=0, microsecond=0)
                end_dt = end_dt.replace(minute=0, second=0, microsecond=0)

            # ----------------------
            # insanity checks
            # -----------------------
            if start_dt >= end_dt:
                raise ValueError("Start must be before end.")
            if start_dt < datetime(2020, 10, 15) or end_dt < datetime(2020, 10, 15):
                raise ValueError("MRMS data before 2020-10-15 does not exist.")

            result["start"] = start_dt
            result["end"] = end_dt
            root.destroy()
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))

    def on_cancel():
        result["start"] = None
        result["end"] = None
        root.destroy()

    # ---------------------------------------------------------- 
    # Lets make some buttons!! you know so we can save stuff 
    # ------------------------------------------------------------
    btn_frame = ttk.Frame(frm)
    btn_frame.grid(row=5, column=0, columnspan=2, pady=(15, 0), sticky="e")

    save_btn = ttk.Button(btn_frame, text="Save", command=on_save)
    save_btn.grid(row=0, column=0, padx=(0, 5))

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=on_cancel)
    cancel_btn.grid(row=0, column=1)

    root.mainloop()
    if result["start"] is None or result["end"] is None:
        return None
    return result["start"], result["end"]



def ask_destination_folder() -> str | None:
    """
    Popup to choose destination folder for MRMS files.
    """
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        title="Select folder to save MRMS files"
    )
    root.destroy()
    if not folder:
        return None
    return folder



def show_completion_popup(saved_files, destination: str):
    """
    Popup summarizing what was saved and where.

    Uses a scrollable list so the window doesn't fill the whole screen.
    """
    root = tk.Tk()
    root.withdraw()

    win = tk.Toplevel(root)
    win.title("MRMS Download")
    win.resizable(True, True)

    frame = ttk.Frame(win, padding=10)
    frame.grid(row=0, column=0, sticky="nsew")

    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

    if saved_files:
        summary_text = f"Download completed. Saved {len(saved_files)} file(s)."
    else:
        summary_text = "Download completed, but no new files were saved."

    ttk.Label(frame, text=summary_text).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 5)
    )

    # Destination folder line
    ttk.Label(
        frame,
        text=f"Destination folder: {destination}",
        anchor="w",
        justify="left",
        wraplength=600,
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))

    ttk.Label(frame, text="Saved files:").grid(
        row=2, column=0, columnspan=2, sticky="w"
    )

    list_frame = ttk.Frame(frame)
    list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(2, 5))

    frame.grid_rowconfigure(3, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    listbox = tk.Listbox(list_frame, height=10, width=80)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)

    listbox.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure(0, weight=1)

    for path in saved_files:
        listbox.insert(tk.END, path)

    btn = ttk.Button(frame, text="Close", command=win.destroy)
    btn.grid(row=4, column=0, columnspan=2, pady=(8, 0))

    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    win.geometry(f"+{x}+{y}")
    win.attributes("-topmost", True)
    win.lift()

    win.grab_set()
    root.wait_window(win)
    root.destroy()



#-------------------------------------------------------------------------------
# Here is the Main part that actually does stuff! The workhorse if you will
#-------------------------------------------------------------------------------
if __name__ == "__main__":
    date_range = ask_date_range()
    if date_range is None:
        print("User cancelled, exiting.")
        sys.exit(0)

    start, end = date_range

    # ------------------------------------------------------- 
    # Well there isn't data before 2015 so we say that here
    # ------------------------------------------------------
    assert start >= datetime(2020, 10, 15), "MRMS data before 2020-10-15 does not exist"
    assert end   >= datetime(2020, 10, 15), "MRMS data before 2020-10-15 does not exist"

    # ---------------------------
    # Ask where to save the files
    # ----------------------------

    dest = ask_destination_folder()
    if not dest:
        print("No folder selected, exiting.")
        sys.exit(0)

    os.makedirs(dest, exist_ok=True)

    hour = timedelta(hours=1)
    date = start

    urls = []
    while date < end:
        url = (
            f"https://mtarchive.geol.iastate.edu/"
            f"{date.year:04d}/{date.month:02d}/{date.day:02d}"
            f"/mrms/ncep/MultiSensor_QPE_01H_Pass2/"
            f"MultiSensor_QPE_01H_Pass2_00.00_"
            f"{date.year:04d}{date.month:02d}{date.day:02d}-"
            f"{date.hour:02d}0000.grib2.gz"
        )
        urls.append(url)
        date += hour

    if not urls:
        print("No files to download in the selected range.")
        show_completion_popup([], dest)
        sys.exit(0)

    # -----------------------------------------------------------
    # Create progress window based on number of files to download
    # ----------------------------------------------------------
    create_progress_window(len(urls))

    chunk_size = 50
    chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]

    all_saved = []
    for block in chunks:
        loop = asyncio.get_event_loop()
        saved_block = loop.run_until_complete(main_async(block, dest))
        all_saved.extend(saved_block)

    # ------------------------------
    # Close the progress bar window
    # --------------------------------
    close_progress_window()

    # -----------------------
    # Final summary popup
    # -------------------------
    show_completion_popup(all_saved, dest)
