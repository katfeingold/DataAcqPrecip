::: ***GridReader.cmd***

::: This batch file is a template for the GridReader MetVue utility.
::: This template demonstrates displaying the built-in usage help documentation for this utility by:
:::    1) Setting variables
:::    2) Setting the working directory
:::    3) Setting allowable maximum heap memory
:::    4) Command-line execution of concatenated settings and the help argument for this utility

@echo off
::: Turn off the console display of the remaining commands in this batch file.

::: Setting for variables to be expanded at execution time rather than at parse time,
::: When delayed expansion is in effect, variables may be referenced using !variable_name!
::: (in addition to the normal %variable_name% )
SETLOCAL EnableDelayedExpansion

::: Use the current directory.
::: Specifically, use the fully qualified file pathname of this batch file's location.
PUSHD %~dp0

::: Location of the HEC-MetVue package, ensure there are no spaces
set MV_HOME="C:\HEC\MetVue\HEC-MetVue3.4"

::: Setting the location of the java executable.
set java="%MV_HOME%/jre/bin/java.exe"

::: Setting the allowable maximum heap memory for use by the jvm.
set memory_setting=-Xmx1024m

::: Set the default time zone for the JVM
set gmtTz=-Duser.timezone=GMT

::: Setting the classpath for running the MetVue program.
set class_path=-cp "%MV_HOME%/metvue/modules/*;%MV_HOME%/metvue/modules/ext/*;%MV_HOME%/platform/modules/*;%MV_HOME%/platform/lib/*;%MV_HOME%/platform/core/*;%APPDATA%/HEC/HEC-MetVue/3.4.0.372/user/*"

::: Setting the library path for running the MetVue program.
set library_path=-Djava.library.path="%MV_HOME%/metvue/modules/lib/amd64"

::: Setting for calling the class to perform the operation of this utility.
set main_method=hec/metvue/base/tin/spatialUtil/GridReader

::: Setting the arguments for this utility. 
::: https://www.hec.usace.army.mil/confluence/cwmsdocs/metum/latest/gridreader-294956929.html - documentation 
::: Use -? to refer to the built-in usage help to select from all the available arguments for this utility.
:: -----------------------------------------------------------------
:: If the py script passed any arguments, use those as "usage_help"
:: Otherwise fall back to the built-in defaults below.
:: -----------------------------------------------------------------
   IF NOT "%~1"=="" (
     SET usage_help=%*
   ) ELSE (
     :: no arguments on the command line → use defaults
     set usage_help= ^
       -inFile "C:\Temp\DataAcquisition\precip\MultiSensor_QPE_01H_Pass2_00.00_*.grib2.gz" ^
       -outFile "C:\Temp\DataAcquisition\precip\DataOutDss\test.dss" ^
       -extentsShapefile "C:\Users\q0heckaf\OneDrive - US Army Corps of Engineers\Projects\00.Videos\MetVueVideos\Models\HEC_MetVue_Zonal_Editor\Maps\Subbasins_Reprojected.shp" ^
       -dssA "SHG" ^
       -dssB "MRMS" ^
       -dssC "Precip" ^
       -dssF "01H"
   )


::: Command-line execution.
%java% %memory_setting% %gmtTz% %library_path% %class_path% %main_method% !usage_help!

::: change back to original directory
POPD

ENDLOCAL

pause