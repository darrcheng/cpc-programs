import numpy as np

cpc = "adi"

headers = {
    "dma": {
        "Time": "datetime",
        "DMA Voltage": "dma_voltage",
        "Electrometer Concentration": "concentration",
        "Time Since Start": "time_since_start",
        "Electrometer Voltage": "voltage",
        "DMA Set Voltage": "dma_set_voltage",
    },
    "adi": [
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
    ],
}

datetime_col = {"adi": "datetime"}

read_settings = {
    "dma": {
        "filetype": ("CSV Files", "DMA*avg.csv*"),
        "datecol": "datetime",
        "tzone": "US/Eastern",
    },
    "adi": {
        "filetype": ("Text Files", "MAGIC*.txt*"),
        "filepattern": "MAGIC*.txt",
        "datecol": "datetime",
        "tzone": "US/Eastern",
    },
}

fit_settings = {"bounds": ([0, 0.1, 0], [1, np.inf, np.inf])}
