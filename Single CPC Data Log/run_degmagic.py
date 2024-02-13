import tkinter as tk
from test_gui import App

root = tk.Tk()
root.title("DEG MAGIC Instrument GUI")
app = App(root, "degmagic_config.yml")
root.mainloop()
