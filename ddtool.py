#!/usr/bin/env python3
import sys
import os
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd

from multicolumn_listbox import Multicolumn_Listbox

import tkinter
from tkinter import ttk
import tkinter.filedialog
import tkinter.font


class DDToolMain(ttk.Frame):
    """The gui and functions."""
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.selected_files = []
        self.selected_files_strvar = tkinter.StringVar()
        self.init_gui()

    def init_gui(self):

        """Builds GUI."""
        self.root.title("DD Tool")
        self.grid(column=0, row=0, sticky='nsew')
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # self.num1_entry = ttk.Entry(self, width=5)
        # self.num1_entry.grid(column=1, row = 2)

        self.open_button = ttk.Button(self, text='Select Files', command=self._selectFiles)
        self.open_button.grid(column=1, row=2, padx=2, pady=2)

        self.num2_entry = ttk.Entry(self, width=5)
        self.num2_entry.grid(column=3, row=2)

        self.answer_frame = ttk.LabelFrame(self, text='Answer')
        self.answer_frame.grid(column=0, row=3, columnspan=4, sticky='nesw')
        self.answer_label = tkinter.Message(self.answer_frame,
                                textvariable=self.selected_files_strvar,
                                )
        # self.answer_label.grid(column=0, row=0)
        # self.answer_label.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
        self.answer_label.pack(expand=True, fill='x')
        self.answer_label.bind("<Configure>", lambda e: self.answer_label.configure(width=e.width-10))

        # Labels that remain constant throughout execution.
        foo = ttk.Label(self, text='Temperature Data Files', font='fixed 14 bold')
        foo.grid(column=0, row=0, columnspan=4, padx=3, pady=3)
        #print(tkinter.font.Font(foo['font']).actual())
        ttk.Label(self, text='Number one').grid(column=0, row=2,
                sticky='w')
        ttk.Label(self, text='Number two').grid(column=2, row=2,
                sticky='w')

        ttk.Separator(self, orient='horizontal').grid(column=0,
                row=1, columnspan=4, sticky='ew')

        # for child in self.winfo_children():
            # child.grid_configure(padx=5, pady=5)

        self.lf = ttk.Labelframe(self, text="Plot Area")
        self.lf.grid(row=4, column=0, columnspan=4, sticky='nwes', padx=3, pady=3)

        self.fig = mpl.figure.Figure(figsize=(5,4), dpi=100)
        # t = np.arange(0.0,3.0,0.01)
        # df = pd.DataFrame({'t':t, 's':np.sin(2*np.pi*t)})
        # ax = fig.add_subplot(111)
        # df.plot(x='t', y='s', ax=ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.lf)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(expand=1)
        
        toolbar = NavigationToolbar2Tk(self.canvas, self.lf)
        toolbar.update()
        # self.canvas._tkcanvas.pack(expand=1)

        self.plot_button = ttk.Button(self.lf, text='Plot', command=self._plot)
        self.plot_button.pack()

        
        self.mc = Multicolumn_Listbox(self, ["column one","column two", "column three"],
                stripped_rows = ("white","#f2f2f2"),
                command=self._on_select,
                adjust_heading_to_content=True,
                cell_anchor="center")
        self.mc.interior.grid(row=5, column=0, columnspan=4, sticky='nwes', padx=3, pady=3)
        
        self.mc.table_data = np.random.randint(0,10, size=(20,3)).tolist()

        self.quit_button = ttk.Button(self, text='Quit', command=self._quit)
        self.quit_button.grid(column=3, row=6, sticky='se', padx=2, pady=2)
        
    def _quit(self):
        self.root.quit()     # stops mainloop
        self.root.destroy()  # this is necessary on Windows to prevent
                             # Fatal Python Error: PyEval_RestoreThread: NULL tstate
    
    def _selectFiles(self):
        self.selected_files = tkinter.filedialog.askopenfilenames(
                                parent=self.root,
                                title='Choose Temperature Files')
        self.selected_files_strvar.set(str(self.selected_files))
        self.mc.table_data = np.random.randint(0,1000, size=(20,3)).tolist()

    def _on_select(self, data):
        print("called command when row is selected")
        print(data)

    def _plot(self):
        self.fig.clear()
        t = np.arange(0.0,3.0,0.01)
        df = pd.DataFrame({'t':t, 's':np.sin(2*np.pi*t)})
        ax = self.fig.add_subplot(111)
        df.plot(x='t', y='s', ax=ax)
        self.canvas.draw()
    
        
if __name__ == '__main__':
    root = tkinter.Tk()
    DDToolMain(root)
    root.mainloop()
