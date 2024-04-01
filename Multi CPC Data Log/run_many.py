import csv
from datetime import datetime
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import yaml

from cpcfnc import CPCSerial


class App:
    def __init__(self, root, config_file):

        # Load config file
        self.config_file = config_file
        self.program_path = os.path.dirname(os.path.realpath(__file__))
        with open(
            os.path.join(self.program_path, self.config_file),
            "r",
            encoding="utf-8",
        ) as f:
            self.config = yaml.safe_load(f)

        self.num_cpcs = self.config["num_cpcs"]

        # Threading related initializations
        self.serial_queues = [queue.Queue() for _ in range(self.num_cpcs)]
        self.stop_threads = threading.Event()

        # Initialize CPC classes
        self.cpcs = []
        for i in range(self.num_cpcs):
            cpc = CPCSerial.CPCSerial(
                self.config[f"cpc{i+1}"],
                self.serial_queues[i],
                self.stop_threads,
                None,
            )
            self.cpcs.append(cpc)

        # Setup tkinter GUI
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Setup CSV file
        self.current_date = time.strftime("%Y%m%d")
        self.cpc_headers = []
        for i in range(self.num_cpcs):
            cpc_header = self.config[f"cpc{i+1}"]["cpc_header"]
            self.cpc_headers.extend(cpc_header)
        self.start_time, self.csv_filepath = self.create_files(self.cpc_headers)

        # Start threads for all CPCs
        for cpc in self.cpcs:
            cpc.start()

        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def check_queue(self):
        # Create new file on new day
        if datetime.now().day != self.start_time.day:
            self.start_time, self.csv_filepath = self.create_files(
                self.cpc_headers
            )

        # Get data from all CPCs
        all_cpc_data = {}
        for i in range(self.num_cpcs):
            try:
                self.data = self.serial_queues[i].get_nowait()
                print(self.data)

            except queue.Empty:
                self.data = dict.fromkeys(
                    self.config[f"cpc{i+1}"]["cpc_header"], np.nan
                )
                print(self.data)
            all_cpc_data[f"cpc{i+1}"] = self.data

        # Write all raw data to CSV file
        all_values = []
        for cpc_data in all_cpc_data.values():
            all_values.extend(cpc_data.values())
        with open(self.csv_filepath, mode="a", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(all_values)

        # Check the queue again after 1s
        self.root.after(1000, self.check_queue)

    def close(self):
        self.stop_threads.set()
        self.root.destroy()

    def create_files(self, header):
        # Create subfolder for current date
        start_time = datetime.now()
        current_date = start_time.strftime("%Y-%m-%d")
        subfolder_path = os.path.join(os.getcwd(), current_date)
        os.makedirs(subfolder_path, exist_ok=True)

        # Create CSV file and writer
        file_datetime = start_time.strftime("%Y%m%d_%H%M%S")
        csv_filename = "MANY_" + file_datetime + ".csv"
        csv_filepath = os.path.join(subfolder_path, csv_filename)

        # Open CSV logging file
        with open(csv_filepath, mode="w", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(header)

        return start_time, csv_filepath


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = App(root, "config.yml")
    root.mainloop()
