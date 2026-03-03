# -*- coding: utf-8 -*-
"""
Download latest complete WPC 2.5km QPF forecast cycle,
uses a Tkinter popup to choose the destination folder.
"""
# -------------------------------------------------
# Author (so you know who to yell at) Kat Feingold
# Last updated: 3/2/2026
# UPdated Change:
# 3/2/2026 - script created
# --------------------------------------------------
import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import async_timeout

import tkinter as tk
from tkinter import filedialog, messagebox

# --------------------------------------------
# URL location
# --------------------------------------------
BASE_URL = "https://ftp.wpc.ncep.noaa.gov/2p5km_qpf"
/
#/ -------------------------------------------------------------------------------
# looks for the most recent complete set (29 files) of WPF on the WPC website
# Yes i know there are probably better ways to do this, but this is how i did it.
# -------------------------------------------------------------------------------
def get_latest_complete_cycle_utc(now_utc: datetime) -> datetime:
    """
    Given current UTC time, return the most recent *complete* WPC QPF cycle time
    (00, 06, 12, 18 UTC).
    """
    safety_margin = timedelta(hours=3)
    cycles = [0, 6, 12, 18]
    latest_cycle = None

    for h in cycles:
        cycle_time = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
        if cycle_time > now_utc:
            cycle_time -= timedelta(days=1)
        if now_utc >= cycle_time + safety_margin:
            if latest_cycle is None or cycle_time > latest_cycle:
                latest_cycle = cycle_time

    if latest_cycle is None:
        h = (now_utc.hour // 6) * 6
        cycle_time = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
        if cycle_time > now_utc:
            cycle_time -= timedelta(days=1)
        latest_cycle = cycle_time

    return latest_cycle


def build_forecast_filenames(cycle: datetime):
    """
    Build 29 filenames: p06m_YYYYMMDDHHfXXX.grb, XXX=006..174 step 6.
    """
    yyyymmddhh = cycle.strftime("%Y%m%d%H")
    offsets = list(range(6, 180, 6))
    return [f"p06m_{yyyymmddhh}f{offset:03d}.grb" for offset in offsets]


async def download_file(session, url, dest_dir):
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


async def download_cycle_files(cycle: datetime, dest_dir: str):
    filenames = build_forecast_filenames(cycle)
    urls = [f"{BASE_URL}/{name}" for name in filenames]

    async with aiohttp.ClientSession() as session:
        tasks = [download_file(session, url, dest_dir) for url in urls]
        await asyncio.gather(*tasks)

# ------------------------------------------------------------------------------------------------------------------
#  TKINTER folder selector, yes there are better ways to do this, but too bad i just learned this way so here it is
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

# --------------------------------------------
# This does the thing!!!!
# --------------------------------------------
def main():
    dest_dir = ask_destination_folder()
    if not dest_dir:
        print("No folder selected, exiting.")
        sys.exit(0)

    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    cycle = get_latest_complete_cycle_utc(now_utc)
    print(f"Using cycle: {cycle.strftime('%Y-%m-%d %H:%M')} UTC")

    fnames = build_forecast_filenames(cycle)
    print(f"Expecting {len(fnames)} files.")
    if len(fnames) != 29:
        print("Warning: unexpected number of forecast hours (should be 29).")

    asyncio.run(download_cycle_files(cycle, dest_dir))
    print("Done.")

if __name__ == "__main__":
    main()
