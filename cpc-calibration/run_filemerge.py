import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
import winsound
import pytz

import inst_param as inst


# dma_data = pd.read_csv('Sample Data/DMA_2022_03_14_15_59_29_avg.csv')
def def_time_col(data, col_header, timezone):
    data[col_header] = pd.to_datetime(data[col_header])
    data[col_header] = (
        data[col_header].dt.round("1s").dt.tz_localize(pytz.timezone(timezone))
    )
    data = data.set_index(col_header)
    return data


def merge_files():
    root = tk.Tk()
    root.withdraw()

    # Read DMA/Electrometer data into dataframe
    dma_input = inst.read_settings["dma"]
    PathNameDMA = filedialog.askopenfilenames(
        title="Import DMA File", filetypes=(dma_input["filetype"],)
    )
    dma_data = pd.read_csv(PathNameDMA[0], index_col=False)
    dma_data = dma_data.rename(columns=inst.headers["dma"])
    dma_data = def_time_col(dma_data, dma_input["datecol"], dma_input["tzone"])
    dma_data = dma_data.add_prefix("elec_")

    # Read CPC data into dataframe
    cpc = inst.cpc
    cpc_input = inst.read_settings[cpc]
    PathNameCPC = filedialog.askopenfilenames(
        title="Import CPC File", filetypes=(cpc_input["filetype"],)
    )
    cpc_data = pd.read_csv(
        PathNameCPC[0], index_col=False, header=0, names=inst.headers[cpc]
    )
    print(cpc_data.head())
    # cpc_data.columns = inst.headers[cpc]
    cpc_data = def_time_col(cpc_data, cpc_input["datecol"], cpc_input["tzone"])
    cpc_data = cpc_data.add_prefix("cpc_")

    print("DMA & CPC Data Imported")

    # Join DMA & CPC data
    final_data_set = dma_data.join(cpc_data, how="left")

    # Save file name
    output_filename = (
        PathNameDMA[0][-27:-17].replace("_", "")
        + "_"
        + PathNameDMA[0][-16:-8].replace("_", "")
        + "_joined_DMA_CPC"
    )

    # Output results to CSV file, for debugging/programing/record keeping
    output_folder = os.path.commonpath([PathNameDMA[0], PathNameCPC[0]])
    output_path = os.path.join(output_folder, output_filename + ".csv")
    final_data_set.to_csv(output_path)

    print("Merge Done")

    # Beep
    winsound.Beep(440, 500)

    return final_data_set


def main():
    merge_files()


if __name__ == "__main__":
    main()
