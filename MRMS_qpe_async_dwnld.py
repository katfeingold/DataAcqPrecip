# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import tkinter as tk
from tkinter import filedialog, simpledialog
import subprocess, sys, os
from pathlib import Path
import tkinter as tk
import nest_asyncio
nest_asyncio.apply()
import asyncio
import aiohttp
import async_timeout

#-------------------------------------------------------------------------------
# Python script taht downloads the MRMS data and saves it in a destination file (HArdcoded)
# This script comes from the HMS team. 
#--------------------------------------------------------------------------------
async def download_coroutine(url, session, destination):
    # Use 'async with' for the asynchronous timeout context manager
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
                print(url)
            return await response.release()

async def main(loop, tmp, destination):

    async with aiohttp.ClientSession() as session:
        tasks = [download_coroutine(url, session, destination) for url in tmp]
        return await asyncio.gather(*tasks)


if __name__ == '__main__':
# ------------------------------------------------------------
# Popup to choose destination for the downloaded GRIB2 files
# ------------------------------------------------------------
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)

    destination = filedialog.askdirectory(
        title="Select folder to SAVE downloaded GRIB2 files"
    )
    if not destination:
        print("No destination selected – aborting.", file=sys.stderr)
        sys.exit(1)

    # Now that we have `destination`, create it if needed:
    os.makedirs(destination, exist_ok=True)
    start = datetime(2021, 10, 1, 0, 0)
    end = datetime(2021, 10, 2, 0, 0)   
    # destination = r"C:\Temp\DataAcquisition\precip"
    
    
    assert start >= datetime(2020,10,15), "MultiSensor MRMS data before 2020-10-15 does not exist, consider looking for GageCorr qpe grids"
    assert end >= datetime(2020,10,15), "MultiSensor MRMS data before 2020-10-15 does not exist, consider looking for GageCorr qpe grids"
    

    hour = timedelta(hours=1)
    os.makedirs(destination, exist_ok=True)
    
    #loop through and see if you already have the file locally
    date = start
    urls = []
    opath = []
    while date < end:
        
        url = 'https://mtarchive.geol.iastate.edu/{:04d}/{:02d}/{:02d}/mrms/ncep/MultiSensor_QPE_01H_Pass2/MultiSensor_QPE_01H_Pass2_00.00_{:04d}{:02d}{:02d}-{:02d}0000.grib2.gz'.format(
        date.year, date.month, date.day, date.year, date.month, date.day, date.hour)

        filename = url.split("/")[-1]
        if not os.path.isfile(destination + os.sep + filename):
            urls.append(url)
            opath.append(destination + os.sep + filename)
        date += hour

    #Split urls into chunks so you wont overwhelm IA mesonet with asyncronous downloads
    chunk_size = 50
    chunked_urls = [urls[i * chunk_size:(i + 1) * chunk_size] for i in range((len(urls) + chunk_size - 1) // chunk_size )]

    for tmp in chunked_urls:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(main(loop, tmp, destination))
        del loop, results

#--------------------------------------------------------------------------
# Runs a Hard Coded batch file location
#--------------------------------------------------------------------------
# cmd = r'"C:\RAMwork\Productpulls\DataAcq\DataAcqPrecip\GridReader.cmd" -inFile foo -dir bar'
# # shell=True allows batch files to run directly
# retcode = subprocess.call(cmd, shell=True)
# print("Batch exited with", retcode)

#-------------------------------------------------------------------------
# Runs batchfile in the same directory as this script
# -------------------------------------------------------------------------
# Finds the current script’s folder location
script_dir = Path(__file__).resolve().parent

# Points to GridReader in that folder
batch_file = script_dir / "GridReader.cmd"
if not batch_file.exists():
    print(f"ERROR: Cannot find {batch_file}", file=sys.stderr)
    sys.exit(1)

# # Need teh arguments for the batch file
# in_file = r"C:\Temp\DataAcquisition\precip\MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz"
# out_dir = r"C:\Temp\DataAcquisition\precip\New folder"
# out_file = r"C:\Temp\DataAcquisition\precip\DataOutDss\test.dss" 
# shape_file = r"C:\Users\q0heckaf\OneDrive - US Army Corps of Engineers\Projects\00.Videos\MetVueVideos\Models\HEC_MetVue_Zonal_Editor\Maps\Subbasins_Reprojected.shp" 
# DSSA = r"SHG" 
# DSSB = r"MRMS" 
# DSSC = r"Precip" 
# DSSD = r"01H"


# # the cmd line that will run
# cmd = (
# f'"{batch_file}" '
# f'-inFile "{in_file}" '
# f'-outFile "{out_file}" '
# f'-extentsShapefile "{shape_file}" '
# f'-dssA "{DSSA}" '
# f'-dssB "{DSSB}" '
# f'-dssC "{DSSC}" '
# f'-dssF "{DSSD}"'
# )

# # run it via the shell
# retcode = subprocess.call(cmd, shell=True)
# print("Batch exited with", retcode)

#--------------------------------------------------------------------
# Set up a single root for all pop-ups
#--------------------------------------------------------------------
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

#-----------------------------------------------------------------------------------
#Asks for the input folder/directory it will take all GRIB2 files in that directory
#-----------------------------------------------------------------------------------
directory = filedialog.askdirectory(title="Choose folder with GRIB2 files")
if not directory:
    print("No folder selected – aborting.", file=sys.stderr)
    sys.exit(1)
in_file = os.path.join(
    directory,
    "MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz"
)
#--------------------------------------------------------------------
# ASks for the output DSS filename, can be existing or new
#--------------------------------------------------------------------
out_file = filedialog.asksaveasfilename(
    title="Choose your output DSS file",
    defaultextension=".dss",
    filetypes=[("DSS files","*.dss"), ("All files","*.*")]
)
if not out_file:
    print("No output file selected – aborting.", file=sys.stderr)
    sys.exit(1)

#--------------------------------------------------------------------
# ASks for the shapefile user wants for clipping 
#--------------------------------------------------------------------

shape_file = filedialog.askopenfilename(
    title="Select your extents shapefile",
    filetypes=[("Shapefiles","*.shp"), ("All files","*.*")]
)
if not shape_file:
    print("No shapefile selected – aborting.", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------------------------
# Asks the user to input DSS code string
# --------------------------------------------------------------------
DSSA = simpledialog.askstring("DSS A", "Enter value for Part A (e.g. SHG):")
if not DSSA:
    print("No DSSA entered – aborting.", file=sys.stderr)
    sys.exit(1)

DSSB = simpledialog.askstring("DSS B", "Enter value for Part B (e.g. MRMS):")
if not DSSB:
    print("No DSSB entered – aborting.", file=sys.stderr)
    sys.exit(1)

DSSC = simpledialog.askstring("DSS C", "Enter value for Part C (e.g. Precip):")
if not DSSC:
    print("No DSSC entered – aborting.", file=sys.stderr)
    sys.exit(1)

DSSD = simpledialog.askstring("DSS F", "Enter value for Part F (e.g. 01H):")
if not DSSD:
    print("No DSSD entered – aborting.", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------------------------
# 5) Build and call GridReader.cmd
# --------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
batch = script_dir / "GridReader.cmd"

cmd_str = (
    f'"{batch}" '
    f'-inFile "{in_file}" '
    f'-outFile "{out_file}" '
    f'-extentsShapefile "{shape_file}" '
    f'-dssA {DSSA!r} -dssB {DSSB!r} '
    f'-dssC {DSSC!r} -dssF {DSSD!r}'
)

print("Running:", cmd_str)    # optional echo
ret = subprocess.call(cmd_str, shell=True)
print("Batch exited with code", ret)