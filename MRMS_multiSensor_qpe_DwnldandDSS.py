# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import subprocess
#import subprocess allows the user to run the batch file. 
import os
import sys
from pathlib import Path
import nest_asyncio
nest_asyncio.apply()
import asyncio
import aiohttp
import async_timeout
#This script requires the pip install of nest_aayncio, asyncio, aoihttp, and async_timeout to run

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

    start = datetime(2021, 10, 1, 0, 0)
    end = datetime(2021, 10, 2, 0, 0)   
    destination = r"C:\Temp\DataAcquisition\precip"
    
    
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
# Section runs a Hard Coded batch file location
#--------------------------------------------------------------------------
# cmd = r'"C:\RAMwork\Productpulls\DataAcq\DataAcqPrecip\GridReader.cmd" -inFile foo -dir bar'
# # shell=True allows batch files to run directly
# retcode = subprocess.call(cmd, shell=True)
# print("Batch exited with", retcode)

#-------------------------------------------------------------------------
# Section runs batchfile in the same directory as this script
# -------------------------------------------------------------------------
# Finds the current script’s folder location
script_dir = Path(__file__).resolve().parent

# Points to GridReader in that folder
batch_file = script_dir / "GridReader.cmd"
if not batch_file.exists():
    print(f"ERROR: Cannot find {batch_file}", file=sys.stderr)
    sys.exit(1)

# Need teh arguments for the batch file
in_file = r"C:\Temp\DataAcquisition\precip\MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz"
out_dir = r"C:\Temp\DataAcquisition\precip\New folder"
out_file = r"C:\Temp\DataAcquisition\precip\DataOutDss\test.dss" 
shape_file = r"C:\Users\q0heckaf\OneDrive - US Army Corps of Engineers\Projects\00.Videos\MetVueVideos\Models\HEC_MetVue_Zonal_Editor\Maps\Subbasins_Reprojected.shp" 
DSSA = r"SHG" 
DSSB = r"MRMS" 
DSSC = r"Precip" 
DSSD = r"01H"


# the cmd line that will run
cmd = (
f'"{batch_file}" '
f'-inFile "{in_file}" '
f'-outFile "{out_file}" '
f'-extentsShapefile "{shape_file}" '
f'-dssA "{DSSA}" '
f'-dssB "{DSSB}" '
f'-dssC "{DSSC}" '
f'-dssF "{DSSD}"'
)

# run it via the shell
retcode = subprocess.call(cmd, shell=True)
print("Batch exited with", retcode)