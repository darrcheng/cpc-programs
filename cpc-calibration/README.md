# Detection Efficiency Calibration Code
## Step 1: Merge DMA and CPC data
Run run_filemerge.py
* Input: .csv files for DMA and CPC data
* Output: file called YYYYMMDD_HHMMSS_joined_DMA_CPC 
* DMA data file should be named "DMA_YYYY_MM_DD_HH_MM_SS_avg.csv"
* DMA and CPC headers can be specified in inst_param.py
* DMA and CPC files should include headers of "datetime" and "concentration"
* Merges DMA and CPC on column named "datetime"
## Step 2: Calculate detection efficiency
Run run_detecteff.py
* Input: 
    * joined DMA and CPC data file(s) created in step 1
    * cpc name -> cpc:string
    * cpc test condition -> ini_temp:list 
    * thab monomer/trimer voltages -> thab:tuple
    * skipped measurements at start/end -> skip:tuple
* Outputs:
    * Detection efficiency csv for each condition
    * Summary detection efficiency csv for all conditions
    * Summary fit parameter csv for all conditions
    * Report file for each condition with the date and input parameters
    * Graph of detection efficiency curve