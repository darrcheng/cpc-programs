from dataclasses import dataclass
from pathlib import Path
from typing import final
import pandas as pd
import datetime as dt
import tkinter as tk
from tkinter import filedialog
import os
import pytz
import matplotlib.pyplot as plt

###############################################################################
data_title = input("Enter Data Title: ")

# Negative or Positive
negative_ions = False

# Calculate size
thabMon = 204
thabTri = 375
thabMonMobilDia = 1.47
thabTriMobilDia = 1.97
mobilityConvSlope = 1 / (
    (thabTri - thabMon) / (thabTriMobilDia - thabMonMobilDia)
)
mobilityConvOffset = thabMonMobilDia - thabMon * mobilityConvSlope

###############################################################################

root = tk.Tk()
root.wm_attributes("-topmost", 1)
root.withdraw()

# Read DMA/Electrometer data into dataframe
PathNameDMA = filedialog.askopenfilenames(
    title="Import DMA File", filetypes=(("CSV Files", "*avg.csv"),)
)
dma_data = pd.read_csv(PathNameDMA[0])
dma_data = dma_data.rename(
    {
        "Time": "datetime",
        "DMA Voltage": "dma_voltage",
        "Electrometer Concentration": "concentration",
        "Time Since Start": "time_since_start",
        "Electrometer Voltage": "voltage",
        "DMA Set Voltage": "dma_set_voltage",
    },
    axis="columns",
)
# dma_data = pd.read_csv('5Ch Sample Data/DMA_2022_11_21_14_23_55_avg.csv')
dma_data["datetime"] = pd.to_datetime(dma_data["datetime"])
dma_data["datetime"] = (
    dma_data["datetime"]
    .dt.round("1s")
    .dt.tz_localize(pytz.timezone("US/Eastern"))
)
dma_data = dma_data.set_index("datetime")
dma_data = dma_data.add_prefix("elec_")

# Read CPC data into dataframe and merge CPCs
PathNameCPC = filedialog.askopenfilenames(
    title="Import CPC File", filetypes=(("Text Files", "MAGIC_CPC*"),)
)
cpc_serial = [filename[-23:-20] for filename in PathNameCPC]
final_data_set = dma_data
for count, filename in enumerate(PathNameCPC):
    cpc_data = pd.read_csv(
        filename,
        index_col=False,
        names=(
            "datetime",
            "instrument_datetime",
            "concentration",
            "temp_conditioner",
            "temp_initiator",
            "temp_moderator",
            "temp_optics",
            "temp_heatsink",
            "temp_pcb",
            "supply_voltage",
            "diff_press",
            "abs_press",
            "flow_rate",
            "time_interval",
            "time_corrected_live",
            "time_dead",
            "raw_counts_low",
            "raw_counts_high",
            "flags",
            "errors",
            "serial_number",
        ),
    )
    cpc_data = cpc_data[cpc_data["serial_number"].notna()]
    cpc_data["instrument_datetime"] = (
        pd.to_datetime(cpc_data["instrument_datetime"])
        .dt.round("1s")
        .dt.tz_localize(pytz.timezone("US/Eastern"))
    )
    cpc_data = cpc_data.set_index("instrument_datetime")
    cpc_data = cpc_data.add_prefix(cpc_serial[count] + "_")
    final_data_set = final_data_set.join(cpc_data, how="left")


# Output results to CSV file, for debugging/programing/record keeping
output_folder = os.path.commonpath([PathNameDMA[0], PathNameCPC[0]])
output_path = os.path.join(
    output_folder, "joined_DMA_5Ch_CPC" + "_" + data_title + ".csv"
)
final_data_set.to_csv(output_path)

# List of columns to calculate detection efficiency
detect_eff_col = [cpc + "_concentration" for cpc in cpc_serial]
detect_eff_col = [
    "elec_dma_voltage",
    "elec_dma_set_voltage",
    "elec_concentration",
] + detect_eff_col


# Create new df for detection efficiency related measurements
detect_eff = final_data_set[detect_eff_col]

# Calculate diameter
detect_eff.insert(
    0,
    "diameter",
    detect_eff["elec_dma_voltage"] * mobilityConvSlope + mobilityConvOffset,
)

# Group, skip first 30 rows, then take average across group
detect_eff_avg = detect_eff.groupby(
    "elec_dma_set_voltage", as_index=False
).apply(
    lambda x: x.iloc[30:]
)  # skip first thirty rows
detect_eff_avg = detect_eff_avg.groupby(
    "elec_dma_set_voltage", as_index=False
).mean()

# Correct Electrometer Measurements
detect_eff_avg["elec_concentration"] = detect_eff_avg["elec_concentration"] * (
    -1 + 2 * negative_ions
)
detect_eff_avg["elec_concentration"] = (
    detect_eff_avg["elec_concentration"]
    - detect_eff_avg.reset_index().at[0, "elec_concentration"]
)

# Calculate Detection Efficiency
for count, cpc in enumerate(cpc_serial):

    detect_eff_avg[cpc + "_detect_eff"] = (
        detect_eff_avg[cpc + "_concentration"]
        / detect_eff_avg["elec_concentration"]
    )


# Output Detection Efficiency to CSV
output_path = os.path.join(
    output_folder, "detect_eff_5Ch_CPC" + "_" + data_title + ".csv"
)
detect_eff_avg.to_csv(output_path)

###############################################################################

# Graph Detection Efficiency by Voltage
plt.figure()
for count, cpc in enumerate(cpc_serial):
    plt.plot(
        detect_eff_avg["elec_dma_voltage"],
        detect_eff_avg[cpc + "_detect_eff"],
        "x",
        label=cpc,
    )

plt.title("CPC Detection Efficiency")
plt.xlabel("DMA Voltage (V)")
plt.ylabel("Detection Efficiency")
plt.legend()

os.makedirs(os.path.join(output_folder, "Graphs"), exist_ok=True)
plt.savefig(
    os.path.join(output_folder, "Graphs", data_title + "_detect_eff_vlt.png"),
    dpi=300,
)

plt.figure()
for count, cpc in enumerate(cpc_serial):
    plt.plot(
        detect_eff_avg["diameter"],
        detect_eff_avg[cpc + "_detect_eff"],
        "x",
        label=cpc,
    )

plt.title("CPC Detection Efficiency")
plt.xlabel("Mobility Diameter (nm)")
plt.ylabel("Detection Efficiency")
plt.legend()

plt.savefig(
    os.path.join(output_folder, "Graphs", data_title + "_detect_eff_dia.png"),
    dpi=300,
)

###############################################################################

# Plot concentration of electrometer, CPC by voltage
fig, (ax1, ax2) = plt.subplots(2, constrained_layout=True, sharex=True)

# Electrometer Concentration Plot
ax1.plot(
    detect_eff_avg["elec_dma_voltage"], detect_eff_avg["elec_concentration"]
)
ax1.set_ylabel("Elec. Concentration (#/cc)")

# CPC Concentration Plot
for count, cpc in enumerate(cpc_serial):
    ax2.plot(
        detect_eff_avg["elec_dma_voltage"],
        detect_eff_avg[cpc + "_concentration"],
        label=cpc,
    )
ax2.set_ylabel("CPC Concentration (#/cc)")
ax2.legend()

# Plot Labels
for ax in (ax1, ax2):
    ax.label_outer()
fig.suptitle("Size Distribution & CPC Concentration")
fig.supxlabel("DMA Voltage (V)")

fig.savefig(
    os.path.join(output_folder, "Graphs", data_title + "_conc_vlt.png"),
    dpi=300,
)

# Plot concentration of electrometer, CPC by diameter
fig, (ax1, ax2) = plt.subplots(2, constrained_layout=True, sharex=True)

# Electrometer Concentration Plot
ax1.plot(detect_eff_avg["diameter"], detect_eff_avg["elec_concentration"])
ax1.set_ylabel("Elec. Concentration (#/cc)")

# CPC Concentration Plot
for count, cpc in enumerate(cpc_serial):
    ax2.plot(
        detect_eff_avg["diameter"],
        detect_eff_avg[cpc + "_concentration"],
        label=cpc,
    )
ax2.set_ylabel("CPC Concentration (#/cc)")
ax2.legend()

# Plot Labels
for ax in (ax1, ax2):
    ax.label_outer()
fig.suptitle("Size Distribution & CPC Concentration")
fig.supxlabel("Mobility Diameter (nm)")

fig.savefig(
    os.path.join(output_folder, "Graphs", data_title + "_conc_dia.png"),
    dpi=300,
)

# Save Analysis Settings
f = open(
    os.path.join(
        output_folder, "pha_analysis_parameters_" + data_title + ".txt"
    ),
    "w",
)
f.writelines(["DMA Analysis File: " + PathNameDMA[0] + "\n"])
for count, filename in enumerate(PathNameCPC):
    f.writelines(
        [
            "CPC Analysis File(s): " + filename + "\n",
        ]
    )
f.writelines(
    [
        "Analysis Date: "
        + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + "\n",
        "THAB Monomer Voltage: " + str(thabMon) + "\n",
        "THAB Trimer Voltage: " + str(thabTri) + "\n",
        "Mobility Conversion Slope: " + str(mobilityConvSlope) + "\n",
        "Mobility Conversion Offset: " + str(mobilityConvOffset) + "\n",
        "Negative Ions? " + str(negative_ions),
    ]
)
f.close()
