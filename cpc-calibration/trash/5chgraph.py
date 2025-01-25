import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import detectionefficiency


def sigmoid(x, eta, dp_50, k, a, c):
    return eta / (1 + np.exp(-k * (x - dp_50))) - np.exp(-a * x + c)


def hill_langmuir_loss(x, k_a, n, loss, q):
    return 1 / (1 + (k_a / x) ** n) - np.exp(-loss * x) + q


# Constants
cpc = "223"
# ini_temps = [98, 96, 91, 86, 81, 76, 71, 61, 40, 35]
ini_temps = [98, 81, 71, 61, 51, 41, 35]
# ini_temps = [99, 35]
thab_mon = 217
thab_tri = 401
skip_start = 10
skip_end = 10

fit_skip = 0
# Loop through settings, calculate, and join detection efficiency data tables
fits = np.arange(0)
prev_plateau = 0
for temp in ini_temps:
    # Data title = Growth tube + Initator Temp
    data_title = cpc + "_" + str(temp)
    print(data_title)

    # Calculate detection efficency
    detect_eff, data_directory = detectionefficiency.calc_cpc_cal(
        data_title, thab_mon, thab_tri, skip_start, skip_end, False
    )
    # print(detect_eff)
    detect_eff[detect_eff == np.inf] = 0
    detect_eff = detect_eff.fillna(0)
    # Merge dataframes
    detect_eff = detect_eff.add_suffix("_" + data_title)
    try:
        combined_detect_eff = combined_detect_eff.join(detect_eff, how="left")
    except:
        combined_detect_eff = detect_eff


# Save combined dataframe with the date
file_date = data_directory[1][0:8]
output_filename = file_date + "_detect_eff_raw_" + cpc + ".csv"
output_path = os.path.join(data_directory[0], output_filename)
combined_detect_eff.to_csv(output_path)

# Plot constants
graph_mode = "Diameter"
graph_title = file_date + "_" + cpc + "_Combined_Raw"

x = np.linspace(1, 10, 100)
plot_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
# Plot detection efficiency vs. diameter for different settings, add legend
plot_legend = ()
for i, temp in enumerate(ini_temps):
    data_title = cpc + "_" + str(temp)
    detectionefficiency.plot_detect_eff(
        graph_mode, graph_title, data_directory[0], combined_detect_eff, 1, "_" + data_title
    )
    plt.figure(1)
    plot_legend = plot_legend + (temp,)
plt.figure(1)
plt.legend(plot_legend)
plt.ylim([0, 1.2])


# Save plot
plt.savefig(
    os.path.join(
        data_directory[0], "Graphs", file_date + "_" + cpc + "_Combined_Raw_detect_eff_dia"
    ),
    dpi=300,
)
# plt.show()
