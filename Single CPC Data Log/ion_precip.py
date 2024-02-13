from datetime import datetime
import time
import os
import csv
import threading
import queue
import tkinter as tk
from tkinter import ttk, font
import traceback
import sys

from labjack import ljm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import yaml

import random

from cpcfnc import *

from test_gui import App


class IonPrecip(App):
    def __init__(self, root, config_file):
        super().__init__(root, config_file)

        # Other window
        self.setup_precip_gui(root)

        # Queue
        self.precip_queue = queue.Queue()

    def setup_precip_gui(self, root):
        ion_win = tk.Toplevel(root)
        ion_win.title("Ion Precipitator Status")
        ion_section = ttk.LabelFrame(ion_win, text="Ion Precipitator")
        ion_section.pack(pady=10, padx=10, fill="x")
        # ion_win.configure(bg="light gray")

        # Entry for Set Voltage
        lbl_set_voltage = ttk.Label(ion_section, text="Set Voltage: ")
        lbl_set_voltage.grid(column=0, row=0, sticky="w")
        self.entry_set_voltage = ttk.Label(ion_section, text="000 V")
        self.entry_set_voltage.grid(column=1, row=0, sticky="w")

        # Entry for Voltage Interval
        lbl_toggle_time = ttk.Label(ion_section, text="Voltage Interval: ")
        lbl_toggle_time.grid(column=0, row=1, sticky="w")
        self.entry_toggle_time = ttk.Label(ion_section, text="00 s")
        self.entry_toggle_time.grid(column=1, row=1, sticky="w")

        # Display fields
        time_label = ttk.Label(ion_section, text="Current Time: ")
        time_label.grid(column=0, row=2, sticky="w")
        self.time_var = ttk.Label(ion_section, text="XX/XX/XXXX XX:XX:XX")
        self.time_var.grid(column=1, row=2, sticky="w")

        monitor_label = ttk.Label(ion_section, text="Voltage Monitor: ")
        monitor_label.grid(column=0, row=4, sticky="w")
        self.monitor_var = ttk.Label(ion_section, text="000 V")
        self.monitor_var.grid(column=1, row=4, sticky="w")

    def update_gui(self):
        super().update_gui()
        self.time_var.config(
            text=f"{self.precip_data['precip_datetime'].strftime('%m/%d/%Y %H:%M:%S')}"
        )
        self.monitor_var.config(
            text=f"{(self.precip_data['precip_voltage']):.1f} V"
        )

    def ion_precip(self):
        # Initalize variables
        state = "OFF"
        toggle_timer = 0.0
        set_voltage = self.config["ion_config"]["precip_volt"]
        toggle_time = self.config["ion_config"]["toggle_seconds"]
        scaling_factor = self.config["ion_config"]["supply_scaling"]
        labjack_io = self.config["labjack_io"]
        polarity = "positive"
        lj_voltage = set_voltage / scaling_factor

        # Update GUI
        self.entry_set_voltage.config(text=f"{set_voltage} V")
        self.entry_toggle_time.config(text=f"{toggle_time} s")

        # Constants for update intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds
        process_name = "Ion Precpitator"

        while not self.stop_threads.is_set():
            precip_data = {"precip_datetime": datetime.now()}
            toggle_timer += 1.0
            try:
                # Toggle voltage
                if toggle_timer >= toggle_time:
                    if state == "ON":
                        # Turn off voltage
                        state = "OFF"
                        self.lj_voltage_off(labjack_io)

                        # Flip polarity
                        polarity = self.flip_polarity(polarity)
                    else:
                        # Turn on voltage
                        state = "ON"
                        self.lj_set_voltage(labjack_io, polarity, lj_voltage)

                        # Reset toggle timer
                    toggle_timer = 0

                # Record voltage monitor
                voltage = (
                    ljm.eReadName(
                        self.handle, labjack_io["voltage_monitor_input"]
                    )
                ) * scaling_factor

                # Add voltage monitor to output data
                precip_data["precip_voltage"] = voltage

                # Add data to queue
                self.precip_queue.put(precip_data)

                # Schedule the next update
                curr_time = commonfnc.sched_update(
                    process_name, curr_time, update_time
                )

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print(f"{process_name}: " + str(ljme) + str(datetime.now()))
                time.sleep(1)

            except Exception as e:
                print(f"Error: {process_name}")
                print(traceback.format_exc())
                raise

        print(f"Shutdown: {process_name}")

    def flip_polarity(self, polarity):
        if polarity == "positive":
            polarity = "negative"
        else:
            polarity = "positive"
        return polarity

    def lj_voltage_off(self, labjack_io):
        ljm.eWriteName(self.handle, labjack_io["voltage_set_pos"], 0)
        ljm.eWriteName(self.handle, labjack_io["voltage_set_neg"], 0)

    def lj_set_voltage(self, labjack_io, polarity, lj_voltage):
        if polarity == "positive":
            # Set Voltage to Labjack
            ljm.eWriteName(
                self.handle,
                labjack_io["voltage_set_pos"],
                lj_voltage,
            )
            ljm.eWriteName(
                self.handle,
                labjack_io["voltage_set_neg"],
                0,
            )

        elif polarity == "negative":
            # Set Voltage to Labjack
            ljm.eWriteName(
                self.handle,
                labjack_io["voltage_set_neg"],
                lj_voltage,
            )
            ljm.eWriteName(
                self.handle,
                labjack_io["voltage_set_pos"],
                0,
            )

    def check_queue(self):
        ## Add Precip
        try:
            self.data = self.serial_queue.get_nowait()
            try:
                self.count_data = self.count_queue.get_nowait()
            except:
                print("No LJ Data")
            try:
                self.precip_data = self.precip_queue.get_nowait()
            except:
                print("No Ion Precipiator Data")

            # Update GUI with new serial data
            self.update_gui()

            # Save data for plotting
            self.update_plot()

            # Log data to CSV
            self.log_data()

        except queue.Empty:
            pass
        finally:
            # Check the queue again after 100ms
            self.root.after(100, self.check_queue)

    def start_thread(self):
        super().start_thread()
        threading.Thread(target=self.ion_precip).start()

    def close_app(self):
        pass

    def start_stop(self):
        pass

    def write_data_row(self):
        write_data = list(self.data.values())
        write_data = [item for sublist in write_data for item in sublist]

        self.csv_writer.writerow(
            write_data
            + list(self.count_data.values())
            + list(self.precip_data.values())
        )

    def write_header(self, f):
        if f.tell() == 0:
            header = (
                self.config["data_config"]["cpc_header"]
                + list(self.count_data.keys())
                + list(self.precip_data.keys())
            )
            self.csv_writer.writerow(header)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = IonPrecip(root, "test_config.yml")
    root.mainloop()
