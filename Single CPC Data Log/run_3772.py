import tkinter as tk
from test_gui import App

root = tk.Tk()
root.title("3772 Instrument GUI")
app = App(root, "3772_config.yml")
root.mainloop()
