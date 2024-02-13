import serial


def serial_startup(data_config):
    ser = serial.Serial(
        port=data_config["serial_port"],
        baudrate=data_config["serial_baud"],
        bytesize=data_config["serial_bytesize"],
        parity=data_config["serial_parity"],
        timeout=data_config["serial_timeout"],
    )
    ser.flushInput()

    # Send startup commands
    if data_config["start_commands"]:
        for start_command in data_config["start_commands"]:
            ser.write((start_command + "\r\n").encode())
            ser.readline().decode().rstrip()

    return ser
