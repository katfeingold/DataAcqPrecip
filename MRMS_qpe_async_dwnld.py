# -*- coding: utf-8 -*-
"""
MRMS downloader with Tkinter dialog for date selection.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

import nest_asyncio
nest_asyncio.apply()

import asyncio
import aiohttp
import async_timeout

import tkinter as tk
from tkinter import ttk, messagebox

#-------------------------------------------------------------------------------
#  Reading from the params.txt file for later use
#-------------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
params_file = script_dir / "params.txt"
if not params_file.exists():
    print(f"ERROR: Cannot find {params_file}", file=sys.stderr)
    sys.exit(1)

params = {}
with open(params_file, "r") as pf:
    for raw in pf:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        params[key.strip()] = val.strip()

try:
    destination = params["destination"]
    in_file     = params["in_file"]
    out_dir     = params.get("out_dir", "")
    out_file    = params["out_file"]
    shape_file  = params["shape_file"]
    DSSA        = params["DSSA"]
    DSSB        = params["DSSB"]
    DSSC        = params["DSSC"]
    DSSF        = params["DSSF"]
except KeyError as e:
    print(f"ERROR: Missing parameter {e} in {params_file}", file=sys.stderr)
    sys.exit(1)

os.makedirs(destination, exist_ok=True)

if out_dir:
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isabs(out_file):
        out_file = os.path.join(out_dir, out_file)

if os.path.isdir(in_file):
    in_file = os.path.join(
        in_file,
        "MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz"
    )

#-------------------------------------------------------------------------------
# ASYNC Diwnload stuff
#-------------------------------------------------------------------------------
async def download_coroutine(url, session, destination):
    async with async_timeout.timeout(1200):
        async with session.get(url) as response:
            if response.status == 200:
                fp = destination + os.sep + os.path.basename(url)
                with open(fp, 'wb') as f_handle:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f_handle.write(chunk)
            else:
                print("FAILED:", url)
            return await response.release()


async def main(loop, url_list, destination):
    async with aiohttp.ClientSession() as session:
        tasks = [
            download_coroutine(u, session, destination)
            for u in url_list
        ]
        return await asyncio.gather(*tasks)

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

    # ------Center a bit------
    root.geometry("+200+200")

    mode_var = tk.StringVar(value="custom")  # "custom" or "lookback"

    # ------Frames------
    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")

    # ------ Mode radio buttons because who doesn't love those ------
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

    # ------ Custom range entries ------
    ttk.Label(frm, text="Start:").grid(row=1, column=0, sticky="e")
    start_entry = ttk.Entry(frm, width=25)
    start_entry.grid(row=1, column=1, sticky="w")

    ttk.Label(frm, text="End:").grid(row=2, column=0, sticky="e")
    end_entry = ttk.Entry(frm, width=25)
    end_entry.grid(row=2, column=1, sticky="w")

    #------ Setting defaults based on current date ------
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    start_entry.insert(0, yesterday.strftime("%d-%b-%Y 00:00"))
    end_entry.insert(0, today.strftime("%d-%b-%Y 00:00"))


    # ------ Lookback ------
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
                # ------ lookback ------
                days_str = lookback_entry.get().strip()
                days = int(days_str)
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=days)
                # ------ snap minutes/seconds to zero to get full day of data ------
                start_dt = start_dt.replace(minute=0, second=0, microsecond=0)
                end_dt = end_dt.replace(minute=0, second=0, microsecond=0)

            # ------insanity checks------
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

    # ------ Lets make some buttons!! you know so we can save stuff ------
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

#-------------------------------------------------------------------------------
# Here is the Main part that actually does stuff! The workhorse if you will
#-------------------------------------------------------------------------------
if __name__ == "__main__":
    date_range = ask_date_range()
    if date_range is None:
        print("User cancelled, exiting.")
        sys.exit(0)

    start, end = date_range

    # ------ Existing assertions and limitation errors ------
    assert start >= datetime(2020, 10, 15), "MRMS data before 2020-10-15 does not exist"
    assert end   >= datetime(2020, 10, 15), "MRMS data before 2020-10-15 does not exist"

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
        fn = os.path.basename(url)
        if not os.path.isfile(os.path.join(destination, fn)):
            urls.append(url)
        date += hour

    chunk_size = 50
    chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]

    for block in chunks:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(loop, block, destination))

    batch = script_dir / "GridReader.cmd"
    if not batch.exists():
        print(f"ERROR: Cannot find {batch}", file=sys.stderr)
        sys.exit(1)

    cmd_str = (
        f'"{batch}" '
        f'-inFile "{in_file}" '
        f'-outFile "{out_file}" '
        f'-extentsShapefile "{shape_file}" '
        f'-dssA {DSSA!r} -dssB {DSSB!r} '
        f'-dssC {DSSC!r} -dssF {DSSF!r}'
    )

    print("Running:", cmd_str)
    ret = subprocess.call(cmd_str, shell=True)
    print("Batch exited with code", ret)
