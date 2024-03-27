import csv
from datetime import datetime
import numpy as np
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

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

        # Threading related initializations
        self.serial_queue = queue.Queue()
        self.count_queue = queue.Queue()
        self.stop_threads = threading.Event()

        # Setup tkinter GUI
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # For logging
        self.current_date = time.strftime("%Y%m%d")

        # Start CPC serial data collection
        self.cpc = CPCSerial.CPCSerial(
            self.config["cpc1"],
            self.serial_queue,
            self.stop_threads,
            None,
        )
        self.start_time, self.csv_filepath = self.create_files(
            self.config["cpc1"]["cpc_header"]
        )
        self.cpc.start()

        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def check_queue(self):
        # Create new file on new day
        if datetime.now().day != self.start_time.day:
            self.start_time, self.csv_filepath = self.create_files(
                self.config["cpc1"]["cpc_header"]
            )
        try:
            self.data = self.serial_queue.get_nowait()
            print(self.data)

        except queue.Empty:
            self.data = dict.fromkeys(self.config["cpc1"]["cpc_header"], np.nan)
            print(self.data)

        all_values = [value for key, value in self.data.items()]

        # Write all raw data to CSV file
        with open(self.csv_filepath, mode="a", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(all_values)

        # if self.config["pulse_count"]:
        #     try:
        #         self.count_data = self.count_queue.get_nowait()
        #     except:
        #         print("No LJ Data")
        # print(self.count_data)

        # # Update GUI with new serial data
        # self.update_gui()

        # # Save data for plotting
        # self.update_plot()

        # # Log data to CSV
        # self.log_data()

        # except queue.Empty:
        #     pass

        # Check the queue again after 1s
        self.root.after(1000, self.check_queue)

    def close(self):
        self.stop_threads.set()
        self.root.destroy()

    def create_files(self, header):
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
