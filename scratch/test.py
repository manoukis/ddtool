import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import BOTH, YES

class AppFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()

    def _create_widgets(self):
        entry = ttk.Entry(self)
        entry.grid(row=0, column=1, sticky='nsew')
        label = ttk.Label(self, text='Name:')
        label.grid(row=0, column=0, sticky='nsew')
        # magic to make things expand on resize
        self.winfo_toplevel().rowconfigure(0, weight=1)
        self.winfo_toplevel().columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

root = tk.Tk()
root.title('Testlication')
frame = AppFrame(root, borderwidth=15, relief='sunken')
frame.pack(fill=BOTH, expand=YES)
root.mainloop()