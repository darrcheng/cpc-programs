import csv
from datetime import datetime
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

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

        # Gather all serial ports into a list
        self.serial_ports = [self.config[f"cpc{i}"]["serial_port"] for i in range(1, self.num_cpcs + 1)]

        # Gather all cpc names into a list
        self.cpc_name = [self.config[f"cpc{i}"]["cpc_name"] for i in range(1, self.num_cpcs + 1)]
        
        # Threading related initializations
        self.serial_queues = [queue.Queue() for _ in range(self.num_cpcs)]
        self.stop_threads = threading.Event()

        # Initialize CPC classes, test=True when testing GUI offline
        self.cpcs = []
        for i in range(self.num_cpcs):
            cpc = CPCSerial.CPCSerial(
                self.config[f"cpc{i+1}"],
                self.serial_queues[i],
                self.stop_threads,
                None, test=True
            )
            self.cpcs.append(cpc)

        # Setup tkinter GUI
        self.root = root
        self.root.title("5 Channel Butanol CPC Data Viewer")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Initialize the GUI components
        self.setup_layout()

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

        # Initialize data structure for plotting
        self.plot_data = {}
        
        # Check the queue every 1s
        root.after(1000, self.check_queue)

    def setup_layout(self):
        # Create the tab control (Notebook)
        tab_control = ttk.Notebook(self.root)

        # Create tabs (as frames)
        settings_tab = ttk.Frame(tab_control)
        plots_tab = ttk.Frame(tab_control)
        overview_tab = ttk.Frame(tab_control)
        serial_tab = ttk.Frame(tab_control)

        # Add tabs to the Notebook
        tab_control.add(settings_tab, text='Settings')
        tab_control.add(plots_tab, text='Data & Plots')
        tab_control.add(overview_tab, text='System Overview')
        tab_control.add(serial_tab, text='Serial Data Monitor')

        # Pack to make the tabs visible
        tab_control.pack(expand=1, fill="both")

        # Call methods to create widgets in each tab instead of frame
        self.create_settings_widgets(settings_tab)
        self.create_plots_widgets(plots_tab)
        self.create_overview_widgets(overview_tab)
        self.create_serial_widgets(serial_tab)

        # Configure the root window's resizing properties
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def create_settings_widgets(self, frame):
        ttk.Label(frame, text="Serial Port:").grid(row=0, column=0, sticky="w")
        self.serial_port_combobox = ttk.Combobox(frame, values=self.serial_ports)
        self.serial_port_combobox.grid(row=0, column=1, sticky="ew")

    def create_plots_widgets(self, frame):
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # You will plot the data in the update_plot function
        # So the initial plot setup can be minimal, just setting labels
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")

        # Store the canvas draw method
        self.graph_canvas = self.canvas.draw

    def create_overview_widgets(self, frame):
        # Create a canvas on which to draw the instruments and their data
        self.canvas = tk.Canvas(frame, width=600, height=300, bg='white')
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Draw rectangles to represent the CPC instruments
        self.draw_instruments(50, 75, [
            ("CPC #1", "1488 cm³", "35.0°C"),
            ("CPC #2", "1638 cm³", "11.0°C"),
            ("CPC #3", "1221 cm³", "34.9°C"),
            ("CPC #4", "1 cm³", "35.0°C"),
            ("CPC #5", "1284 cm³", "35.0°C"),
        ])

    def draw_instrument(self, x, y, title, concentration, temperature):
        # Draw a column
        self.canvas.create_rectangle(x, y, x+30, y+100, outline='black', fill='lightgrey')
        # Draw sections within the column
        self.canvas.create_line(x, y+30, x+30, y+30, fill='black')
        self.canvas.create_line(x, y+70, x+30, y+70, fill='black')
        # Add labels to the sections
        self.canvas.create_text(x+15, y+10, text=concentration)
        self.canvas.create_text(x+15, y+30, text=temperature)
        self.canvas.create_text(x+15, y+50, text='...')
        self.canvas.create_text(x+15, y+70, text='...')
        self.canvas.create_text(x+15, y+90, text='...')
        # Draw a top for the column
        # self.canvas.create_rectangle(x-10, y-30, x+40, y, outline='black', fill='darkgrey')
        # Add a title below the base
        self.canvas.create_text(x+15, y+120, text=title, font=('Arial', 10, 'bold'))

    def draw_instruments(self, start_x, start_y, instrument_data):
        padding = 100  # Space between each column
        for i, (title, concentration, temperature) in enumerate(instrument_data):
            # Calculate the x coordinate for each instrument
            x = start_x + i * padding
            self.draw_instrument(x, start_y, title, concentration, temperature)

    def create_serial_widgets(self, serial_tab):
        # Serial port selection
        ttk.Label(serial_tab, text="Select Serial Port:").pack(side=tk.TOP, fill=tk.X)
        # Assuming you have a list of serial port configurations in your config
        self.serial_port_combobox = ttk.Combobox(serial_tab, values=self.serial_ports)
        self.serial_port_combobox.pack(side=tk.TOP, fill=tk.X)
        self.serial_port_combobox.bind('<<ComboboxSelected>>', self.on_combobox_select)

        # Serial data display
        self.serial_data_text = tk.Text(serial_tab, height=20, width=80)
        self.serial_data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for serial data Text widget
        serial_data_scrollbar = ttk.Scrollbar(serial_tab, orient="vertical", command=self.serial_data_text.yview)
        serial_data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.serial_data_text.config(yscrollcommand=serial_data_scrollbar.set)

    def on_combobox_select(self, event=None):
        # Clear existing data
        self.serial_data_text.delete('1.0', tk.END)
        # Get the index of the selected serial port to reference the correct queue
        selected_index = self.serial_port_combobox.current()
        self.selected_queue = self.serial_queues[selected_index]
        # Trigger an immediate update
        self.update_serial_data_display()

    def update_serial_data_display(self):
        if hasattr(self, 'selected_queue'):
            while not self.selected_queue.empty():
                # Retrieve the latest data from the selected queue
                serial_output = self.selected_queue.get_nowait()
                # Create a formatted string of all key-value pairs
                message = "\n".join(f"{key}: {value}" for key, value in serial_output.items())
                self.serial_data_text.insert(tk.END, message + "\n\n")
                # Auto-scroll to the end
                self.serial_data_text.see(tk.END)
        
        # Schedule the next check in 1 second
        self.root.after(1000, self.update_serial_data_display)


    def check_queue(self):
        # Create new file on new day
        if datetime.now().day != self.start_time.day:
            self.start_time, self.csv_filepath = self.create_files(
                self.cpc_headers
            )
        all_cpc_data = {}

        # Get data from all CPCs and store for plotting and writing to CSV
        for i in range(self.num_cpcs):
            try:
                data_point = self.serial_queues[i].get_nowait()
                print(data_point)

                # Extract cpc_name from the data_point
                cpc_name = self.cpc_name[i]
                if cpc_name not in self.plot_data:
                    self.plot_data[cpc_name] = {'datetime': [], 'concentration': []}

                # Parse datetime and concentration, add to the plot data structure
                parsed_datetime = data_point['datetime']
                concentration = float(data_point['concentration'])
                self.plot_data[cpc_name]['datetime'].append(parsed_datetime)
                self.plot_data[cpc_name]['concentration'].append(concentration)

                all_cpc_data[cpc_name] = data_point

            except queue.Empty:
                pass

        self.update_plot()

        # Write all raw data to CSV file if all_cpc_data is populated
        if all_cpc_data:  # Checks if there's any data collected
            with open(self.csv_filepath, mode="a", newline="") as data_file:
                data_writer = csv.writer(data_file, delimiter=",")
                # Create a list that will hold one entry per CPC for this timestamp
                row = []
                for name in self.cpc_name:  # Ensuring the order of data in the CSV
                    if name in all_cpc_data:
                        # Assuming all_cpc_data[name] is a dictionary containing all necessary data fields
                        row.extend(list(all_cpc_data[name].values()))
                    else:
                        # Extend row with NaNs or some placeholder if no data for this CPC
                        row.extend([np.nan] * len(self.config[f"cpc1"]["cpc_header"]))  # Adjust the number as per data fields

                data_writer.writerow(row)
            

        # Check the queue again after 1s
        self.root.after(1000, self.check_queue)

    def update_plot(self):
        # Clear the previous plot
        self.ax.clear()

        # Plot data for each CPC
        for cpc_name, cpc_data in self.plot_data.items():
            if cpc_data['datetime']:  # Check if there is data to plot
                # Plot the updated data with a label for the legend
                self.ax.plot(cpc_data['datetime'], cpc_data['concentration'], label=cpc_name)

        # Format the x-axis to display the datetime properly
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        # Add labels, legend, and rescale the axes
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Particle Count, particles/cm³")
        self.ax.legend()
        self.ax.autoscale_view()

        # Redraw the canvas
        self.graph_canvas()
        # Schedule the next update
        self.root.after(1000, self.update_plot) # assuming 1-second intervals for updates
    

    def close(self):
        self.stop_threads.set()
        print("Closing application...")
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
    app = App(root, "config.yml")
    root.mainloop()
