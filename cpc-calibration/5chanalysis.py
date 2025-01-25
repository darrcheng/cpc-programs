import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import datetime as dt

import detectionefficiency
import inst_param as inst
import fitfunc


# Constants
cpc = "SN210"
# ini_temps = [98, 96, 91, 86, 81, 76, 71, 61, 40, 35]
# ini_temps = [98, 81, 71, 61, 51, 41, 35]
ini_temps = [90]
# thab_mon = 228
# thab_tri = 425
# skip_start = 10
# skip_end = 10
skip = (10, 10)  # (start_skip, end_skip)
thab = (228, 425)  # (thabMon, thabTri)
negative_ions = False

fit_skip = 0
# Loop through settings, calculate, and join detection efficiency data tables
fits = np.arange(0)
for temp in ini_temps:
    # Data title = Growth tube + Initator Temp
    data_title = cpc + "_" + str(temp)
    print(data_title)

    # Calculate detection efficency
    detect_eff, data_directory = detectionefficiency.calc_cpc_cal(
        data_title, thab, skip, negative_ions
    )

    detect_eff[detect_eff == np.inf] = 0
    detect_eff = detect_eff.fillna(0)
    detect_eff.loc[
        detect_eff["elec_concentration"] < 50, "Detection Efficiency"
    ] = 0

    print(detect_eff.head())

    x = detect_eff.loc[fit_skip:, "Diameter"].values
    y = detect_eff.loc[fit_skip:, "Detection Efficiency"].values
    try:
        popt, _ = curve_fit(
            fitfunc.cpc_eta_activ_w_GK,
            x,
            y,
            bounds=inst.fit_settings["bounds"],
            maxfev=5000,
        )
    except:
        popt = np.zeros(len(inst.fit_settings["bounds"][0]))
    print(popt)
    fits = np.append(fits, popt)

    # Merge dataframes
    detect_eff = detect_eff.add_suffix("_" + data_title)
    try:
        combined_detect_eff = combined_detect_eff.join(detect_eff, how="left")
    except:
        combined_detect_eff = detect_eff

fits = fits.reshape(len(ini_temps), len(popt))

# Save combined dataframe with the date
file_date = data_directory[1][0:8]
output_filename = file_date + "_detect_eff_" + cpc + ".csv"
output_path = os.path.join(data_directory[0], output_filename)
combined_detect_eff.to_csv(output_path)

# Save fits
fits_output_filename = file_date + "_fits_" + cpc + ".csv"
fits_output_path = os.path.join(data_directory[0], fits_output_filename)
np.savetxt(fits_output_path, fits, delimiter=",")

# Save report
report_output_filename = file_date + "_report_" + cpc + ".txt"
report_output_path = os.path.join(data_directory[0], report_output_filename)


def generate_analysis_report(output_path, negative_ions, thab, skip):
    f = open(output_path, "w")

    f.writelines(
        [
            "Analysis Date: "
            + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + "\n",
            "THAB Monomer Voltage: " + str(thab[0]) + "\n",
            "THAB Trimer Voltage: " + str(thab[1]) + "\n",
            "Negative Ions? " + str(negative_ions),
            "Start Skip: " + str(skip[0]) + "\n",
            "End Skip: " + str(skip[1]) + "\n",
        ]
    )
    f.close()


generate_analysis_report(report_output_path, negative_ions, thab, skip)


# Plot constants
graph_mode = "Diameter"
graph_title = file_date + "_" + cpc + "_Combined"
x = np.linspace(1, 15, 100)
plot_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

# Plot detection efficiency vs. diameter for different settings, add legend
plot_legend = ()
for i, temp in enumerate(ini_temps):
    data_title = cpc + "_" + str(temp)
    fig, ax = detectionefficiency.plot_detect_eff(
        graph_mode,
        graph_title,
        data_directory[0],
        combined_detect_eff,
        1,
        "_" + data_title,
    )
    ax.plot(x, fitfunc.cpc_eta_activ_w_GK(x, *fits[i, :]), color=plot_colors[i])
    plot_legend = plot_legend + (temp,) + (None,)
ax.set_ylim([0, 1.2])
ax.legend(plot_legend)

# Save plot
fig.savefig(
    os.path.join(
        data_directory[0],
        "Graphs",
        file_date + "_" + cpc + "_Combined_detect_eff_dia",
    ),
    dpi=300,
)
# plt.show()
