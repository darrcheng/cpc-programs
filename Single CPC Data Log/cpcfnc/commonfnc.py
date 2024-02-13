import time
import os
from datetime import datetime


def sched_update(process_name, curr_time, update_time):
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


def get_log_filename(cpc):
    # Create a folder named '3025 data' if it doesn't exist
    if not os.path.exists("CPC Data"):
        os.makedirs("CPC Data")

    # Generate the filename based on the current date
    filename = time.strftime(
        f"{cpc}_%Y%m%d.csv"
    )  # Change the extension to .csv
    return os.path.join("CPC Data", filename)
