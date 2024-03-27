# Import libraries
from datetime import datetime
import threading
import time
import traceback

import serial


class CPCSerial:
    def __init__(self, config, data_queue, stop_event, stop_barrier):
        self.config = config
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.stop_barrier = stop_barrier

        self.process_name = self.config["cpc_name"]
        self.thread = threading.Thread(target=self.record_serial_data)

    def start(self):
        self.thread.start()

    def serial_startup(self):
        self.ser = serial.Serial(
            port=self.config["serial_port"],
            baudrate=self.config["serial_baud"],
            bytesize=self.config["serial_bytesize"],
            parity=self.config["serial_parity"],
            timeout=self.config["serial_timeout"],
        )
        self.ser.flushInput()

    def serial_startup_commands(self):
        if self.config["start_commands"]:
            for start_command in self.config["start_commands"]:
                self.ser.write((start_command + "\r\n").encode())
                self.ser.readline().decode().rstrip()

    def record_serial_data(self):
        # Setup CPC serial connection
        self.serial_startup()

        # Send startup commands
        self.serial_startup_commands()

        curr_time = time.monotonic()

        # Loop until stop event is set
        while not self.stop_event.is_set():
            try:
                # Store responses in a list
                responses = []

                if self.config["serial_commands"]:
                    for command in self.config["serial_commands"]:
                        # Send command to serial port
                        self.ser.write((command + "\r").encode())

                        # Read response from serial port
                        response = self.ser.readline().decode().rstrip()
                        response = response.split(",")

                        # Append response to the list
                        responses.extend(response)
                else:
                    # Read response from serial port
                    response = self.ser.readline().decode().rstrip()
                    response = response.split(",")

                    # Append response to the list
                    responses = response

                # Create dictionary with responses
                responses = [self.process_name, datetime.now()] + responses
                serial_output = dict(zip(self.config["cpc_header"], responses))

                # Modify concentration
                if not self.config["default_flow"]:
                    calc_conc = (
                        float(serial_output["1 second counts"])
                        / self.config["cpc_flowrate"]
                    )
                    serial_output["concentration"] = "{:.2f}".format(calc_conc)

                # Share CPC data with other threads
                self.data_queue.put(serial_output)

                # Schedule the next update
                curr_time = sched_update(self.process_name, curr_time)

            except Exception as e:
                print(f"Error: {self.process_name}")
                print(traceback.format_exc())


def sched_update(process_name, curr_time, update_time=1):
    # Calculate sleep time based on seconds till next update
    next_time = curr_time + update_time - time.monotonic()

    # Set sleep time to 0 if program is behind
    if next_time < 0:
        # Skip loops if the program is behind
        missed_loops = abs(next_time) / update_time
        if missed_loops > 1:
            curr_time = curr_time + update_time * int(missed_loops)
        next_time = 0
        print(f"Slow: {process_name}" + str(datetime.now()))

    # Sleep
    time.sleep(next_time)

    # Update current time for next interval
    curr_time = curr_time + update_time
    return curr_time
