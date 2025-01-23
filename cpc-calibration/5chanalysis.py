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


def mu_g(T_degC=20):
    """Returns the air viscosity [kg/m-s]"""
    T_K = T_degC + 273.15
    mu_g_r = 1.83 * 10**-5  # reference gas viscosity [kg/m-s]
    T_r = 296.15  # reference temperature [K]
    P_r = 101.3  # reference pressure [kPa]
    Suth = 110.4  # Sutherland const. [K]
    mu = mu_g_r * (T_r + Suth) / (T_K + Suth) * (T_K / T_r) ** (3 / 2)
    return mu


def lambda_mfp(T_degC=20, P_kPa=101.3):
    """Returns the gas mean free path [m]"""
    T_K = T_degC + 273.15
    lambda_mfp_r = 6.73 * 10**-8  # reference mean free path [m]
    T_r = 296.15  # reference temperature [K]
    P_r = 101.3  # reference pressure [kPa]
    Suth = 110.4  # Sutherland const. [K]

    lam = (
        lambda_mfp_r
        * (P_r / P_kPa)
        * (T_K / T_r)
        * (1 + Suth / T_r)
        / (1 + Suth / T_K)
    )
    return lam


def Kn(Dp, T_degC=20, P_kPa=101.3):
    """Returns the Knudsen number"""
    Dp = np.array([Dp]).flatten()
    Dp_SI = Dp * 1e-9
    Kn = 2 * lambda_mfp(T_degC, P_kPa) / Dp_SI

    return Kn if len(Kn) > 1 else Kn[0]


def Cc(Dp, T_degC=20, P_kPa=101.3):
    """Returns the Cunningham slip correction factor"""
    Cc_alpha, Cc_beta, Cc_gamma = 1.142, 0.558, 0.999  # Cc constants
    Kn_num = Kn(Dp, T_degC, P_kPa)
    Cc = 1 + Kn_num * (Cc_alpha + Cc_beta * np.exp(-Cc_gamma / Kn_num))

    return Cc if len(Cc) > 1 else Cc[0]


def GK_eta(Dp, L_tube, Q_lpm=0.3, T_degC=20, P_kPa=101.3):
    """Gormley-Kennedy (1949) particle transmission efficiency
    in laminar flow through a tube"""
    T_K = T_degC + 273.15
    # Dp = np.array([Dp]).flatten()
    Dp_SI = Dp * 1e-9
    k_Bltz = 1.380658e-23  # Boltzmann constant [J/K]
    Dc = (
        k_Bltz
        * T_K
        * Cc(Dp, T_degC, P_kPa)
        / (3 * np.pi * mu_g(T_degC) * Dp_SI)
    )  # Diffusion coefficient [m^2/s]
    Q_SI = Q_lpm * 0.001 / 60  # flowrate [m^3/s]
    xi = Dc * (L_tube * np.pi / Q_SI)

    # next lines calculate eta for xi<0.02 or xi>0.02
    eta_xi_lt_p02 = (
        1 - 2.5638 * xi ** (2 / 3) + 1.2 * xi + 0.1767 * xi ** (4 / 3)
    )  # xi<=0.02
    eta_xi_gt_p02 = (
        0.81905 * np.exp(-3.6568 * xi)
        + 0.09753 * np.exp(-22.305 * xi)
        + 0.0325 * np.exp(-56.961 * xi)
        + 0.01544 * np.exp(-107.62 * xi)
    )  # xi>0.02
    eta = eta_xi_lt_p02 * (xi <= 0.02) + eta_xi_gt_p02 * (xi > 0.02)

    return eta  # if len(eta) > 1 else eta[0]


def cpc_eta_activation(x, eta, d50, d0):
    """Returns CPC activation efficiency according to Stolzenburg & McMurry (1991)
    formulation (ultrafine-CPC)"""
    x = np.array([x]).flatten()
    y = eta * (1 - np.exp(-np.log(2) * (x - d0) / (d50 - d0)))
    y[y < 0] = 0

    return y  # if len(y) > 1 else y[0]


def cpc_eta_activ_w_GK(x, eta, d50, d0, L=0.05, Q=0.3, T_degC=20, P_kPa=101.3):
    """Returns CPC activation efficiency multiplied with
    Gormley-Kennedy transmission efficiency"""
    y = cpc_eta_activation(x, eta, d50, d0) * GK_eta(x, L, Q, T_degC, P_kPa)
    y[y < 0] = 0

    return y  # if len(y) > 1 else y[0]


# Constants
cpc = "tomato_jen"
# ini_temps = [98, 96, 91, 86, 81, 76, 71, 61, 40, 35]
# ini_temps = [98, 81, 71, 61, 51, 41, 35]
ini_temps = ["37"]
thab_mon = 228
thab_tri = 425
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
    if temp == 35:
        detect_eff.loc[len(detect_eff.index)] = [
            0,
            0,
            0,
            1000,
            100,
            prev_plateau,
        ]
    prev_plateau = detect_eff.iat[-1, -1]
    detect_eff.loc[
        detect_eff["Electrometer Concentration"] < 50, "Detection Efficiency"
    ] = 0
    # detect_eff = detect_eff[detect_eff["Detection Efficiency"] > 0.01]

    print(detect_eff.head())

    x = detect_eff.loc[fit_skip:, "Diameter"].values
    y = detect_eff.loc[fit_skip:, "Detection Efficiency"].values
    # print(x)
    # print(y)
    try:
        # popt, _ = curve_fit(
        #     sigmoid,
        #     x,
        #     y,
        #     p0=[1, 1, 1, 1, 1],
        #     bounds=([0.7, 0, -np.inf, 0.5, -np.inf], [1, 7, np.inf, np.inf, 5]),
        #     maxfev=5000,
        # )
        # popt, _ = curve_fit(
        #     cpc_eta_activ_w_GK,
        #     x,
        #     y,
        #     bounds=([0, 0.1, 0], [1, np.inf, np.inf]),
        #     maxfev=5000,
        # )
        popt, _ = curve_fit(
            cpc_eta_activ_w_GK,
            x,
            y,
            bounds=([0, 0.1, 0, 0], [2, np.inf, np.inf, np.inf]),
            maxfev=5000,
        )

        # popt, _ = curve_fit(
        #     hill_langmuir_loss,
        #     x,
        #     y,
        #     p0=[1, 1, 0.5, -0.1],
        #     bounds=(-np.inf, [np.inf, np.inf, np.inf, 0]),
        # )
    except:
        popt = np.zeros(3)
        # try:
        #     # popt, _ = curve_fit(
        #     #     hill_langmuir_loss,
        #     #     x,
        #     #     y,
        #     #     method="dogbox",
        #     #     bounds=(-np.inf, [np.inf, np.inf, np.inf, 0]),
        #     # )
        #     popt, _ = curve_fit(
        #         sigmoid,
        #         x,
        #         y,
        #         method="dogbox",
        #         bounds=(
        #             [-np.inf, -np.inf, -np.inf, 1, -np.inf, -np.inf],
        #             [np.inf, np.inf, np.inf, np.inf, 1, np.inf],
        #         ),
        #     )
        # except:
        #     popt = np.zeros(5)
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

# Plot constants
graph_mode = "Diameter"
graph_title = file_date + "_" + cpc + "_Combined"

x = np.linspace(1, 15, 100)
plot_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
# Plot detection efficiency vs. diameter for different settings, add legend
plot_legend = ()
for i, temp in enumerate(ini_temps):
    data_title = cpc + "_" + str(temp)
    detectionefficiency.plot_detect_eff(
        graph_mode,
        graph_title,
        data_directory[0],
        combined_detect_eff,
        1,
        "_" + data_title,
    )
    plt.figure(1)
    plt.plot(x, cpc_eta_activ_w_GK(x, *fits[i, :]), color=plot_colors[i])
    # plt.plot(x, hill_langmuir_loss(x, *fits[i, :]), color=plot_colors[i])
    plot_legend = plot_legend + (temp,) + ("_Hide",)
plt.figure(1)
plt.ylim([0, 1.2])

plt.plot(
    [2.425, 3.229, 4.043, 5.676, 8.005, 16.131],
    [0.804, 0.861, 0.895, 0.98, 1.004, 1.016],
    "x",
)
plot_legend = plot_legend + ("Wiendensoher et al. 1990 NaCl",)
plt.plot(
    [
        2.093,
        2.2,
        2.343,
        2.478,
        2.59,
        2.723,
        2.84,
        2.963,
        3.13,
        3.144,
        3.689,
        3.836,
        4.02,
        4.327,
        4.543,
    ],
    [
        0.067,
        0.093,
        0.142,
        0.206,
        0.279,
        0.358,
        0.442,
        0.525,
        0.625,
        0.612,
        0.828,
        0.847,
        0.878,
        0.919,
        0.935,
    ],
    "x",
)
plot_legend = plot_legend + ("Stolzenburg & McMurry 1991 NaCl",)
plt.plot(
    [
        2.803,
        2.886,
        2.949,
        3.036,
        3.139,
        3.264,
        3.427,
        3.626,
        3.89,
        4.364,
        4.84,
        5.399,
        6.045,
        6.743,
        7.625,
        8.406,
        9.285,
    ],
    [
        0.032,
        0.167,
        0.273,
        0.371,
        0.467,
        0.572,
        0.664,
        0.75,
        0.828,
        0.899,
        0.934,
        0.951,
        0.961,
        0.964,
        0.973,
        0.976,
        0.974,
    ],
    "x",
)
plot_legend = plot_legend + ("Keston et al. 1991 NaCl",)
plt.legend(plot_legend)

# Save plot
plt.savefig(
    os.path.join(
        data_directory[0],
        "Graphs",
        file_date + "_" + cpc + "_Combined_detect_eff_dia",
    ),
    dpi=300,
)
# plt.show()
