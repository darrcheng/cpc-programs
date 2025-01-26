# Condensation Particle Counter Programs
Condensation particle counters (CPCs) are used to count the number concentration of aerosol particles. CPCs grow particles to a size detectable by optical counters through condensation of a supersaturated working fluid. This repository contains two collections of scripts 
* Scripts to monitor and record CPC concentration data and operating parameters through a serial connection. 
* Scripts to calculate the detection efficiency (percent of particles observed vs. size)

## Getting Started
### Installing
* Clone the repository
* Install the prerequisite packages `docs\requirements.txt`

### Setup
* Set up the `cpc-log\config.yml` for the CPC(s)

### Running
* GUI can be started using `cpc-log\run_many.py`
* Details on the cpc-calibration scripts can be found in `cpc-calibration\README.md`

## Authors
Contributor Names

Darren Cheng

Ziheng Zeng

## License
This code is licensed under the MIT license