# -*- coding: utf-8 -*-
"""
This script downloads MRMS data (MultiSensor_QPE_01H_Pass2) for a hard‐coded
date range, then calls GridReader.cmd to slice/clip into a DSS.
All inputs (paths, DSS parts, etc.) are read from params.txt in the same folder.
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

#-------------------------------------------------------------------------------
# 0) READ PARAMETERS FROM params.txt
#-------------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
params_file = script_dir / "params.txt"
if not params_file.exists():
    print(f"ERROR: Cannot find {params_file}", file=sys.stderr)
    sys.exit(1)

# Simple key=value parser (ignores blank lines and lines starting with #)
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

# Required values
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

# Prepare directories
os.makedirs(destination, exist_ok=True)

if out_dir:
    os.makedirs(out_dir, exist_ok=True)
    # if out_file is not absolute, join with out_dir
    if not os.path.isabs(out_file):
        out_file = os.path.join(out_dir, out_file)

# If in_file is just a directory, append the expected glob
if os.path.isdir(in_file):
    in_file = os.path.join(in_file,
                           "MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz")


#-------------------------------------------------------------------------------
# Python script that downloads the MRMS data and saves it in a destination file
# (Hard‐coded date range; comes from the HMS team.)
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
                # print URLs that failed
                print("FAILED:", url)
            return await response.release()

async def main(loop, url_list, destination):
    async with aiohttp.ClientSession() as session:
        tasks = [
            download_coroutine(u, session, destination)
            for u in url_list
        ]
        return await asyncio.gather(*tasks)

if __name__ == "__main__":
    # ------------------------------------------------------------------------
    # Set your date range here
    start = datetime(2021, 10, 1, 0, 0)
    end   = datetime(2021, 10, 2, 0, 0)

    assert start >= datetime(2020,10,15), "MRMS data before 2020-10-15 does not exist"
    assert end   >= datetime(2020,10,15), "MRMS data before 2020-10-15 does not exist"

    hour = timedelta(hours=1)
    date = start

    # build list of urls to download (skip ones already on disk)
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

    # chunk into blocks of 50
    chunk_size = 50
    chunks = [urls[i:i+chunk_size] for i in range(0, len(urls), chunk_size)]

    for block in chunks:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(loop, block, destination))

    #--------------------------------------------------------------------------
    # 5) Build and call GridReader.cmd
    #--------------------------------------------------------------------------
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