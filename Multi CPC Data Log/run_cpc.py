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
        self.cpc.start()

        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def check_queue(self):
        try:
            self.data = self.serial_queue.get_nowait()
            print(self.data)

        except queue.Empty:
            self.data = dict.fromkeys(self.config["cpc1"]["cpc_header"], np.nan)
            print(self.data)

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

        finally:
            # Check the queue again after 1s
            self.root.after(1000, self.check_queue)

    def close(self):
        self.stop_threads.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = App(root, "config.yml")
    root.mainloop()
