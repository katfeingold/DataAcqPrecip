# -*- coding: utf-8 -*-
"""
Download latest complete WPC 2.5km QPF forecast cycle,
uses a Tkinter popup to choose the destination folder,
then calls GridReader.cmd (HEC-MetVue utility) using params_qpf.txt.
"""
# ---------------------------------------------------------------
# Author (so you know who to yell at) Kat Feingold
# Last updated: 3/2/2026
# Updated Changes:
# 3/2/2026 - script created
# 3/2/2026 - added GridReader.cmd call driven by params_qpf.txt
# ----------------------------------------------------------------
import os
import sys
import asyncio
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import async_timeout

import tkinter as tk
from tkinter import filedialog, messagebox

# --------------------------------------------
# URL location for WPC QPF
# --------------------------------------------
BASE_URL = "https://ftp.wpc.ncep.noaa.gov/2p5km_qpf"

# --------------------------------------------
# Load params_qpf.txt (GridReader settings)
# --------------------------------------------
script_dir = Path(__file__).resolve().parent
params_file = script_dir / "params_qpf.txt"
if not params_file.exists():
    print(f"ERROR: Cannot find {params_file}", file=sys.stderr)
    sys.exit(1)

# Simple key = value parser (same style as MRMS script)
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
    # destination/in_file may be overridden by GUI later
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

# --------------------------------------------
# Find latest complete WPC QPF cycle (00/06/12/18)
# --------------------------------------------
def get_latest_complete_cycle_utc(now_utc: datetime) -> datetime:
    """
    Given current UTC time, return the most recent *complete* WPC QPF cycle time
    (00, 06, 12, 18 UTC), using a safety margin to allow files to finish posting.
    """
    safety_margin = timedelta(hours=3)  # buffer after nominal cycle time
    cycles = [0, 6, 12, 18]
    latest_cycle = None

    for h in cycles:
        # Start from today's date with given cycle hour
        cycle_time = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
        # If that time is in the future, back up to yesterday
        if cycle_time > now_utc:
            cycle_time -= timedelta(days=1)
        # Only consider cycles whose full set should exist by now
        if now_utc >= cycle_time + safety_margin:
            if latest_cycle is None or cycle_time > latest_cycle:
                latest_cycle = cycle_time

    # Fallback: pick the nearest past cycle if nothing met safety_margin
    if latest_cycle is None:
        h = (now_utc.hour // 6) * 6
        cycle_time = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
        if cycle_time > now_utc:
            cycle_time -= timedelta(days=1)
        latest_cycle = cycle_time

    return latest_cycle

# --------------------------------------------
# Build expected QPF filenames for a cycle
# --------------------------------------------
def build_forecast_filenames(cycle: datetime):
    """
    Build 29 filenames:
    p06m_YYYYMMDDHHfXXX.grb, XXX = 006, 012, ..., 174.
    """
    yyyymmddhh = cycle.strftime("%Y%m%d%H")
    offsets = list(range(6, 180, 6))
    return [f"p06m_{yyyymmddhh}f{offset:03d}.grb" for offset in offsets]

# --------------------------------------------
# Async single-file downloader
# --------------------------------------------
async def download_file(session, url, dest_dir):
    """
    Download one file to dest_dir if it does not already exist.
    Uses a .part temp file and then renames on success.
    """
    local_name = os.path.basename(url)
    local_path = os.path.join(dest_dir, local_name)
    if os.path.exists(local_path):
        print(f"Exists, skipping: {local_name}")
        return

    try:
        async with async_timeout.timeout(600):
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"FAILED {resp.status}: {url}")
                    return
                tmp_path = local_path + ".part"
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024 * 32)
                        if not chunk:
                            break
                        f.write(chunk)
                os.replace(tmp_path, local_path)
                print(f"Downloaded: {local_name}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

# --------------------------------------------
# Async download of all files in a cycle
# --------------------------------------------
async def download_cycle_files(cycle: datetime, dest_dir: str):
    """
    Build all expected URLs for the cycle and download them concurrently.
    """
    filenames = build_forecast_filenames(cycle)
    urls = [f"{BASE_URL}/{name}" for name in filenames]

    async with aiohttp.ClientSession() as session:
        tasks = [download_file(session, url, dest_dir) for url in urls]
        await asyncio.gather(*tasks)

# ------------------------------------------------------------------------------------------------------------------
# TKINTER folder selector, yes there are better ways to do this, but too bad
# this is the way we are doing it here.
# ------------------------------------------------------------------------------------------------------------------
def ask_destination_folder() -> str | None:
    """
    Show a minimal Tkinter dialog to choose a destination folder.
    Returns the selected path or None if cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # hide main window

    folder = filedialog.askdirectory(
        title="Select destination folder for WPC QPF files"
    )
    root.destroy()

    if not folder:
        return None
    return folder

# ---------------------------------------------------
# Call GridReader.cmd using params and chosen folder
# ---------------------------------------------------
def run_gridreader_for_qpf(dest_dir: str):
    """
    Build and execute the GridReader.cmd call for the downloaded QPF files,
    using parameters from params_qpf.txt.
    """
    # -----------------------------------------------------------------
    # Ensure output directory (if any) exists and resolve out_file path
    # -----------------------------------------------------------------
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        if not os.path.isabs(out_file):
            out_path = os.path.join(out_dir, out_file)
        else:
            out_path = out_file
    else:
        out_path = out_file

    # -----------------------------------------------------------------
    # Override destination/in_file from params with users choice
    # If in_file is a directory, append the QPF pattern
    # -------------------------------------------------------------------
    global destination, in_file
    destination = dest_dir
    if os.path.isdir(in_file):
        in_file = os.path.join(dest_dir, "p06m_*.grb")

    # -----------------------------------------------------------
    # Locate GridReader.cmd in the same directory as this script
    # -----------------------------------------------------------
    batch = script_dir / "GridReader.cmd"
    if not batch.exists():
        print(f"ERROR: Cannot find {batch}", file=sys.stderr)
        return

    # -------------------------------------------------------------------------------------------------------
    # Build the command string exactly how GridReader.cmd expects it
    # 'cuase it is very tempermentaland if you don't give it exactly what it wants it throws a temper tantrum
    # ---------------------------------------------------------------------------------------------------------
    cmd_str = (
        f'"{batch}" '
        f'-inFile "{in_file}" '
        f'-outFile "{out_path}" '
        f'-extentsShapefile "{shape_file}" '
        f'-dssA {DSSA!r} -dssB {DSSB!r} '
        f'-dssC {DSSC!r} -dssF {DSSF!r}'
    )

    print("Running GridReader:", cmd_str)
    # -----------------------------------------------------------------------------------------
    # Use shell=True to match the MRMS script behavior which i made first, so its my template
    # Yes i'm sure there are better/easier ways to do this, but meh
    # ------------------------------------------------------------------------------------------
    ret = subprocess.call(cmd_str, shell=True)
    print("GridReader exited with code", ret)

# --------------------------------------------
# This does the thing!!!!
# --------------------------------------------
def main():
    # ------------------------------------------- 
    # Ask user where to put the QPF GRIB files
    # --------------------------------------------
    dest_dir = ask_destination_folder()
    if not dest_dir:
        print("No folder selected, exiting.")
        sys.exit(0)

    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------------
    # Determine the latest complete QPF cycle, this will just pull the most recent QPF
    # --------------------------------------------------------------------------------
    now_utc = datetime.now(timezone.utc)
    cycle = get_latest_complete_cycle_utc(now_utc)
    print(f"Using cycle: {cycle.strftime('%Y-%m-%d %H:%M')} UTC")

    # ------------------------------------------------------------------
    # Show how many files we expect since we need a full set of QPF
    # -------------------------------------------------------------------
    fnames = build_forecast_filenames(cycle)
    print(f"Expecting {len(fnames)} files.")
    if len(fnames) != 29:
        print("Warning: unexpected number of forecast hours (should be 29).")

    # --------------------------------------------------
    # Download the GRIB files for this entire forecast
    # --------------------------------------------------
    asyncio.run(download_cycle_files(cycle, dest_dir))
    print("Downloads complete.")

    # -------------------------------------------------------------------------------
    # Run GridReader.cmd to process the downloaded GRIBs into DSS (or other output)
    # -------------------------------------------------------------------------------
    run_gridreader_for_qpf(dest_dir)

    print("Done with QPF + GridReader workflow.")

if __name__ == "__main__":
    main()
