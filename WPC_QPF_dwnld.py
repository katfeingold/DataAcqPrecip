# -*- coding: utf-8 -*-
"""
Download latest complete WPC 2.5km QPF forecast cycle,
uses a Tkinter popup to choose the destination folder,
then calls NCGribExtractor.cmd (HEC-MetVue utility).
"""
# ----------------------------------------------------------------
# Author (so you know who to yell at) Kat Feingold
# Last updated: 3/2/2026
# Updated Changes:
# 3/2/2026 - script created
# 3/2/2026 - added GridReader.cmd call driven by params_qpf.txt
# 3/3/2026 - switched to NCGribExtractor.cmd for GRIB extraction
# -----------------------------------------------------------------
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
# Load params_qpf.txt (settings)
# --------------------------------------------
script_dir = Path(__file__).resolve().parent
params_file = script_dir / "params_qpf.txt"
if not params_file.exists():
    print(f"ERROR: Cannot find {params_file}", file=sys.stderr)
    sys.exit(1)

#--------------------------------------------------------------------
# Simple key = value parser (same style as MRMS script)
#  ---------------------------------------------------------------
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
    # -----------------------------------------------------------
    # destination may be overridden by Users choice later
    # -----------------------------------------------------------
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
        # -----------------------------------
        # Start from today's date with hour
        # -----------------------------------
        cycle_time = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
        # ---------------------------------------------------
        # If that time is in the future, back up to yesterday
        # yes i know its weird, but i messed up the script twice before i put this in.
        # so here it is, take it out if you want to
        # ----------------------------------------------------
        if cycle_time > now_utc:
            cycle_time -= timedelta(days=1)
        # -------------------------------------------------------------
        # Only look at data sets whose full set should exist by now
        # ------------------------------------------------------------
        if now_utc >= cycle_time + safety_margin:
            if latest_cycle is None or cycle_time > latest_cycle:
                latest_cycle = cycle_time

    # ---------------------------------------------------------------------------------------------------
    # Just in case all that failed pick the nearest past set 
    # -----------------------------------------------------------------------------------------------
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
    Saves with original .grb filename.
    """
    remote_name = os.path.basename(url)          # p06m_YYYYMMDDHHf006.grb
    local_name = remote_name                     # keep .grb
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
# Call NCGribExtractor.cmd using chosen folder
# ---------------------------------------------------
def run_ncgribextractor_for_qpf(dest_dir: str):
    """
    Build and execute the NCGribExtractor.cmd call for the downloaded QPF files.
    Runs once per .grb file in dest_dir.
    """
    # -----------------------------------------------------------------
    # Ensure output directory (if any) exists and resolve FLT out folder
    # -----------------------------------------------------------------
    if out_dir:
        flt_out_dir = out_dir
    else:
        flt_out_dir = os.path.join(dest_dir, "QPF_FLT")

    os.makedirs(flt_out_dir, exist_ok=True)

    # -----------------------------------------------------------------
    # Locate NCGribExtractor.cmd in the same directory as this script
    # -----------------------------------------------------------------
    nc_batch = script_dir / "NCGribExtractor.cmd"
    if not nc_batch.exists():
        print(f"ERROR: Cannot find {nc_batch}", file=sys.stderr)
        return

    # -----------------------------------------------------------------
    # Variable name in the GRIB file to extract
    # You MUST adjust this to match your WPC QPF variable definition
    # (check with NCGribExtractor -info or MetVue's GRIB viewer)
    # -----------------------------------------------------------------
    variable_name = "Total_precipitation_surface_layer_6_Hour_Accumulation"

    # Loop over all .grb files in dest_dir
    for fname in os.listdir(dest_dir):
        if not fname.lower().endswith(".grb"):
            continue

        input_path = os.path.join(dest_dir, fname)
        input_norm = input_path.replace("\\", "/")
        out_norm = flt_out_dir.replace("\\", "/")

        # -------------------------------------------------------------------------------------------------------
        # Build the command string exactly how NCGribExtractor.cmd expects it
        # 'cause it is very tempermental and if you don't give it exactly what it wants it throws a temper tantrum
        # ---------------------------------------------------------------------------------------------------------
        cmd_str = (
            f'"{nc_batch}" '
            f'-inputFile "{input_norm}" '
            f'-variable "{variable_name}" '
            f'-outputDirectory "{out_norm}"'
        )

        print("Running NCGribExtractor:", cmd_str)
        # -----------------------------------------------------------------------------------------
        # Use shell=True to match the MRMS script behavior which i made first, so its my template
        # Yes i'm sure there are better/easier ways to do this, but meh
        # ------------------------------------------------------------------------------------------
        ret = subprocess.call(cmd_str, shell=True)
        print(f"NCGribExtractor exited with code {ret} for {fname}")

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
    # Run NCGribExtractor.cmd to process the downloaded GRIBs into FLT (or other) files
    # -------------------------------------------------------------------------------
    run_ncgribextractor_for_qpf(dest_dir)

    print("Done with QPF + NCGribExtractor workflow.")


if __name__ == "__main__":
    main()

