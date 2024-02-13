from datetime import datetime
import time
import os
import csv
import threading
import queue
import tkinter as tk
from tkinter import ttk
import traceback
import sys

from labjack import ljm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import yaml

import random

from cpcfnc import *


class App:
    def __init__(self, root, config_file):
        # Load config file
        self.config_file = config_file
        self.program_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(self.program_path, self.config_file), "r") as f:
            self.config = yaml.safe_load(f)

        if self.config["pulse_count"]:
            # Load Labjack
            self.handle = ljm.openS("T7", "ANY", self.config["labjack"])
            info = ljm.getHandleInfo(self.handle)
            value = 0
            print(
                "Setting LJM_USB_SEND_RECEIVE_TIMEOUT_MS to %.00f milliseconds\n"
                % value
            )
            LJMError = ljm.writeLibraryConfigS(
                "LJM_USB_SEND_RECEIVE_TIMEOUT_MS", value
            )

        # Threading related initializations
        self.serial_queue = queue.Queue()
        self.count_queue = queue.Queue()
        self.stop_threads = threading.Event()

        # Setup tkinter GUI
        self.root = root
        self.setup_gui(root)

        # For logging
        self.current_date = time.strftime("%Y%m%d")

        # Check the queue every 100ms
        root.after(100, self.check_queue)

    def check_queue(self):
        try:
            self.data = self.serial_queue.get_nowait()
            if self.config["pulse_count"]:
                try:
                    self.count_data = self.count_queue.get_nowait()
                except:
                    print("No LJ Data")
            # print(self.count_data)

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

    def update_plot(self):
        # Create a 2 minute data buffer
        if self.config["cpc"] == "3025":
            self.plot_buffer.append(float(self.data["RD"][0]))
        elif self.config["cpc"] == "3772":
            self.plot_buffer.append(float(self.data["RALL"][0]))
        elif self.config["cpc"] == "degmagic":
            self.plot_buffer.append(float(self.data["default"][1]))
        if len(self.plot_buffer) > 120:
            self.plot_buffer.pop(0)

        # Plot last two minutes of data
        self.ax.clear()
        x_data = list(reversed(range(len(self.plot_buffer))))
        self.ax.plot(x_data, self.plot_buffer, "o")
        self.ax.set_ylabel("Concentration [/cc]")
        y_max = max(self.plot_buffer) * 1.1
        self.ax.set_ylim([0, y_max])
        self.ax.invert_xaxis()
        self.canvas.draw()

    def update_gui(self):
        # # Update GUI
        if self.config["cpc"] == "3025":
            self.concentration_var.config(text=f"{self.data['RD'][0]} /cc")
            self.counts_var.config(text=self.data["RB"][0])
            self.condensor_var.config(
                text=f"{self.data['R1'][0]} \N{DEGREE SIGN}C"
            )
            self.saturator_var.config(
                text=f"{self.data['R2'][0]} \N{DEGREE SIGN}C"
            )
            self.optics_var.config(
                text=f"{self.data['R3'][0]} \N{DEGREE SIGN}C"
            )
            self.flow_var.config(text=f"{self.data['R4'][0]} cm\u00b3/s")
            self.fill_status_var.config(text=self.data["R0"][0])
            self.ready_status_var.config(text=self.data["R5"][0])
            self.pulse_counts_var.config(text=self.count_data["pulse counts"])

        elif self.config["cpc"] == "3772":
            self.concentration_var.config(text=f"{self.data['RALL'][0]} /cc")
            self.counts_var.config(text=self.data["RCOUNT1"])
            self.condensor_var.config(
                text=f"{self.data['RALL'][3]} \N{DEGREE SIGN}C"
            )
            self.saturator_var.config(
                text=f"{self.data['RALL'][2]} \N{DEGREE SIGN}C"
            )
            self.optics_var.config(
                text=f"{self.data['RALL'][4]} \N{DEGREE SIGN}C"
            )
            self.flow_var.config(text=f"{self.data['RSF'][0]} cm\u00b3/min")
            self.fill_status_var.config(text=self.data["RALL"][10])
            self.ready_status_var.config(text=self.data["R5"][0])

        elif self.config["cpc"] == "degmagic":
            self.concentration_var.config(text=f"{self.data['default'][1]} /cc")
            self.counts_var.config(text=self.data["default"][19])
            self.condensor_var.config(
                text=f"{self.data['default'][7]} \N{DEGREE SIGN}C"
            )
            self.saturator_var.config(
                text=f"{self.data['default'][8]} \N{DEGREE SIGN}C"
            )
            self.optics_var.config(
                text=f"{self.data['default'][10]} \N{DEGREE SIGN}C"
            )
            self.flow_var.config(
                text=f"{self.data['default'][15]} cm\u00b3/min"
            )
            self.fill_status_var.config(text=self.data["default"][10])
            self.ready_status_var.config(text=self.data["default"][22])

    def start_thread(self):
        # Clear flag from stop theads
        self.stop_threads.clear()

        # Buffer for plotting
        self.plot_buffer = []

        # Start threads
        threading.Thread(target=self.serial_read).start()
        if self.config["pulse_count"]:
            threading.Thread(target=self.cpc_conc).start()

        # Reconfigure start/stop button
        self.start_stop_button.config(text="Stop", command=self.stop_thread)

    def stop_thread(self):
        # Stop threads
        self.stop_threads.set()

        # Configure start button
        self.start_stop_button.config(text="Start", command=self.start_thread)

    def setup_gui(self, root):
        # Left Frame
        left_frame = ttk.Frame(root)
        left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        # Padding to push the contents down
        ttk.Label(left_frame, text="").pack(pady=30)

        # Top Section
        top_section = ttk.LabelFrame(left_frame, text="Concentration & Counts")
        top_section.pack(pady=10, fill="x")

        self.concentration_var = ttk.Label(
            top_section, text="0 /cc", font=("Arial", 24)
        )
        self.concentration_var.grid(row=0, column=1, sticky="w", columnspan=4)

        ttk.Label(top_section, text="Serial Counts:").grid(
            row=1, column=0, sticky="w"
        )
        self.counts_var = ttk.Label(top_section, text="0")
        self.counts_var.grid(row=1, column=1, sticky="w")

        ttk.Label(top_section, text="Pulse Counts:").grid(
            row=1, column=2, sticky="w", padx=20
        )
        self.pulse_counts_var = ttk.Label(top_section, text="0")
        self.pulse_counts_var.grid(row=1, column=3, sticky="w")

        # Bottom Section
        bottom_section = ttk.LabelFrame(left_frame, text="Instrument Status")
        bottom_section.pack(pady=10, fill="x")

        # Add Start/Stop Button
        self.start_stop_button = ttk.Button(
            left_frame, text="Start", command=self.start_thread
        )
        self.start_stop_button.pack(pady=10)

        # Column 1 in Bottom Section
        ttk.Label(bottom_section, text="Condensor:").grid(
            row=0, column=0, sticky="w"
        )
        self.condensor_var = ttk.Label(
            bottom_section, text="00.0 \N{DEGREE SIGN}C"
        )
        self.condensor_var.grid(row=0, column=1, sticky="w")

        ttk.Label(bottom_section, text="Saturator:").grid(
            row=1, column=0, sticky="w"
        )
        self.saturator_var = ttk.Label(
            bottom_section, text="00.0 \N{DEGREE SIGN}C"
        )
        self.saturator_var.grid(row=1, column=1, sticky="w")

        ttk.Label(bottom_section, text="Optics:").grid(
            row=2, column=0, sticky="w"
        )
        self.optics_var = ttk.Label(
            bottom_section, text="00.0 \N{DEGREE SIGN}C"
        )
        self.optics_var.grid(row=2, column=1, sticky="w")

        # Column 2 in Bottom Section
        ttk.Label(bottom_section, text="Flow:").grid(
            row=0, column=2, sticky="w", padx=20
        )
        self.flow_var = ttk.Label(bottom_section, text="0.00 cm\u00b3/s")
        self.flow_var.grid(row=0, column=3, sticky="w")

        ttk.Label(bottom_section, text="Fill Status:").grid(
            row=1, column=2, sticky="w", padx=20
        )
        self.fill_status_var = ttk.Label(bottom_section, text="0")
        self.fill_status_var.grid(row=1, column=3, sticky="w")

        ttk.Label(bottom_section, text="Ready Status:").grid(
            row=2, column=2, sticky="w", padx=20
        )
        self.ready_status_var = ttk.Label(bottom_section, text="0")
        self.ready_status_var.grid(row=2, column=3, sticky="w")

        # Right Frame (Matplotlib Graph)
        right_frame = ttk.Frame(root)
        right_frame.grid(row=0, column=1, sticky="ns", padx=10, pady=10)

        self.figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.plot([1, 2, 3], [1, 2, 3])  # Sample plot
        self.ax.set_ylabel("Concentration [/cc]")
        self.ax.invert_xaxis()

        self.canvas = FigureCanvasTkAgg(self.figure, right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def serial_read(self):  # , stop_threads, close_barrier, data_config):
        # Constants for CPC serial intervals
        process_name = "CPC Serial Read"
        curr_time = time.monotonic()
        update_time = 1  # seconds

        # Pull out serial_config
        data_config = self.config["data_config"]

        # Set up the serial port and write startup serial commands
        ser = serialfnc.serial_startup(data_config)

        # Record serial data
        while not self.stop_threads.is_set():
            try:
                # Store responses in a list
                responses = {"datetime": [datetime.now()]}

                if data_config["serial_commands"]:
                    for command in data_config["serial_commands"]:
                        # Send command to serial port
                        ser.write((command + "\r").encode())

                        # Read response from serial port
                        response = ser.readline().decode().rstrip()
                        response = response.split(",")

                        # Append response to the list
                        responses[command] = response
                else:
                    # Read response from serial port
                    response = ser.readline().decode().rstrip()
                    response = response.split(",")

                    # Append response to the list
                    responses["default"] = response

                # Modify concentration
                if not data_config["default_flow"]:
                    calc_conc = (
                        float(responses["RB"][0]) / data_config["cpc_flowrate"]
                    )
                    responses["RD"] = ["{:.2f}".format(calc_conc)]

                # Share CPC data with other threads
                self.serial_queue.put(responses)

                # Schedule the next update
                curr_time = commonfnc.sched_update(
                    process_name, curr_time, update_time
                )

            except Exception as e:
                print(f"Error: {process_name}")
                print(traceback.format_exc())
                # raise

        print(f"Shutdown: {process_name}")
        # ser.close()
        # close_barrier.wait()

    def log_data(self):
        log_filename = commonfnc.get_log_filename(self.config["cpc"])

        # If the date changes, reset the current date
        if self.current_date != time.strftime("%Y%m%d"):
            self.current_date = time.strftime("%Y%m%d")

        # Open the log file for the day
        with open(log_filename, "a", newline="") as f:
            self.csv_writer = csv.writer(f)

            # If the file is new/empty, add the header
            self.write_header(f)

            # Write the data
            self.write_data_row()

    def write_data_row(self):
        write_data = list(self.data.values())
        write_data = [item for sublist in write_data for item in sublist]

        if "self.count_data" in locals():
            write_data = write_data + list(self.count_data.values())
        self.csv_writer.writerow(write_data)

    def write_header(self, f):
        if f.tell() == 0:
            header = self.config["data_config"]["cpc_header"]
            if "self.count_data" in locals():
                header = header + list(self.count_data.keys())
            self.csv_writer.writerow(header)

    def cpc_conc(self):
        cpc_config = self.config["data_config"]
        labjack_io = self.config["labjack_io"]
        # Initalize counter and set previous counts and time
        prev_time, prev_count = self.init_lj_counting()
        count_error = False

        # Constants for update intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds
        process_name = "CPC Pulse Counting"
        while not self.stop_threads.is_set():
            count_data = {}
            count_data["count_datetime"] = datetime.now()
            try:
                # Try to reset the Labjack if it errors out
                if count_error:
                    try:
                        (
                            prev_time,
                            prev_count,
                        ) = self.init_lj_counting()
                        print("Connected to LabJack device!")
                        count_error = False
                    except ljm.LJMError:
                        print("Failed to connect to LabJack device.")

                # Clear variables used measuring pulse width
                pulse_width_list = []
                pulses = 0
                pulse_error = 0
                pulse_counter = time.monotonic()
                pulse_width_error = 0
                pulse_width = 0.0
                pulse_zero = 0
                raw_pulse_width = 0.0

                # # If counts are too high, don't pulse count
                # if shared_var.curr_count < 1e6:
                # Repeatedly measure the pulse width and keep an error counter
                while (time.monotonic() - pulse_counter) < (
                    update_time * 0.8
                ) and not self.stop_threads.is_set():
                    pulse_width_single = ljm.eReadName(
                        self.handle,
                        labjack_io["width"] + "_EF_READ_A_F_AND_RESET",
                    )
                    if pulse_width_single < 1 and pulse_width_single > 0:
                        pulse_width = pulse_width + pulse_width_single
                    elif pulse_width_single == 0:
                        pulse_zero = pulse_zero + 1
                    else:
                        pulse_error = pulse_error + 1
                    pulses = pulses + 1
                    # time.sleep(0.002)
                # else:
                #     shared_var.concentration = -9999
                #     shared_var.pulse_width = -9999
                # raw_pulse_width = 0
                # print(pulse_width)
                # print(
                #     f"Pulse Width Good: {pulses-pulse_zero-pulse_error} Pulse Zero: {pulse_zero} Pulse Width Errors:{pulse_error}"
                # )

                # Read the current count from the high-speed counter
                count = ljm.eReadName(
                    self.handle, labjack_io["counter"] + "_EF_READ_A"
                )
                curr_count = count - prev_count
                count_data["pulse counts"] = curr_count

                # Calculate the elapsed time since the last count
                count_time = time.monotonic()
                elapsed_time = count_time - prev_time

                # Calculate the true pulse width from counts and measured pulse width
                good_pulses = pulses - pulse_error - pulse_zero
                if (good_pulses) > 0:
                    pulse_width = pulse_width * ((curr_count) / (good_pulses))
                    # Calculate error assuming pulse errors are due to short pulses
                    if pulse_width > 0:
                        pulse_width_error = (
                            pulse_error * 50e-9 / pulse_width * 100
                        )
                else:
                    pulse_width = 0
                count_data["pulse width"] = pulse_width
                count_data["good pulses"] = good_pulses
                # print(f"Corrected  PW {pulse_width}")

                # Calculate the concentration
                if elapsed_time - pulse_width > 0:
                    concentration = (count - prev_count) / (
                        (elapsed_time - pulse_width)
                        * cpc_config["cpc_flowrate"]
                    )
                else:
                    concentration = -9999
                count_data["pulse conc"] = concentration

                # Calculate the no deadtime concentration
                if elapsed_time > 0:
                    concentration_nodead = (count - prev_count) / (
                        (elapsed_time) * cpc_config["cpc_flowrate"]
                    )
                else:
                    concentration_nodead = -9999
                count_data["pulse conc nodead"] = concentration_nodead
                self.count_queue.put(count_data)

                # Set the previous count and time for the next iteration
                prev_time = count_time
                prev_count = count

                # Schedule the next update
                curr_time = commonfnc.sched_update(
                    process_name, curr_time, update_time
                )

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print(f"{process_name}: " + str(ljme) + str(datetime.now()))
                count_error = True
                time.sleep(1)

            except Exception as e:
                print(f"Error: {process_name}")
                print(traceback.format_exc())
                raise

        print(f"Shutdown: {process_name}")
        # close_barrier.wait()

    def init_lj_counting(self):
        labjack_io = self.config["labjack_io"]
        # Disable clocks 1, 2, 0
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK1_ENABLE", 0)
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK2_ENABLE", 0)
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK0_ENABLE", 0)
        # Set divisor to 1, T7 = 80 MHz
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK0_DIVISOR", 0)
        # Set roll to 4294967295
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK0_ROLL_VALUE", 0)
        # Enable clock 0
        ljm.eWriteName(self.handle, "DIO_EF_CLOCK0_ENABLE", 1)

        ## Configure the specified high-speed counter to read pulses
        # Disable high-speed counter
        ljm.eWriteName(self.handle, labjack_io["counter"] + "_EF_ENABLE", 0)
        # Set input as counter
        ljm.eWriteName(self.handle, labjack_io["counter"] + "_EF_INDEX", 7)
        # Enable high-speed counter
        ljm.eWriteName(self.handle, labjack_io["counter"] + "_EF_ENABLE", 1)

        ## Configure pulse width in
        # Disable pulse width
        ljm.eWriteName(self.handle, labjack_io["width"] + "_EF_ENABLE", 0)
        # Set to one shot
        ljm.eWriteName(self.handle, labjack_io["width"] + "_EF_CONFIG_A", 0)
        # Set input as pulse width
        ljm.eWriteName(self.handle, labjack_io["width"] + "_EF_INDEX", 5)
        # Set to clock 0
        ljm.eWriteName(self.handle, labjack_io["width"] + "_EF_OPTIONS", 0)
        # Enable pulse width
        ljm.eWriteName(self.handle, labjack_io["width"] + "_EF_ENABLE", 1)

        # Initialize time variables and previous count
        prev_time = time.monotonic()
        prev_count = ljm.eReadName(
            self.handle, labjack_io["counter"] + "_EF_READ_A_AND_RESET"
        )
        return prev_time, prev_count


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = App(root, "test_config.yml")
    root.mainloop()
