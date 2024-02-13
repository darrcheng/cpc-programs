import tkinter as tk
from ion_precip import IonPrecip

root = tk.Tk()
root.title("3025 Instrument GUI")
app = IonPrecip(root, "3025_config.yml")
root.mainloop()
