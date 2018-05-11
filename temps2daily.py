#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import tkinter.filedialog
from multicolumn_listbox import Multicolumn_Listbox

import numpy as np
import pandas as pd
from collections import OrderedDict as ordereddict

class App(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.tfiles = ordereddict()
        self.stations = []
        self.selected_files_strvar = tk.StringVar()
        self.root.title("DD Tool")
        self.pack(fill=tk.BOTH, expand=1)

        ## Temperature files area
        foo = ttk.Label(self, text='Temperature Data Files', font='fixed 14 bold')
        foo.pack(fill=tk.X, expand=0, padx=3, pady=3)

        # multicolumnlisbox
        # Frame, for scrollbar placement
        mcf = ttk.Frame(self)
        mcf.pack(fill=tk.BOTH, expand=1, side=tk.TOP, padx=0, pady=0)
        # multicolumn listbox widget
        self.mc = Multicolumn_Listbox(mcf, ["station",
                                            "first date",
                                            "last date",
                                            "number",
                                            "filename"],
                stripped_rows = ("white","#f2f2f2"),
                command=self._on_select,
                adjust_heading_to_content=True,
                cell_anchor="center")
        # scrollbars
        ysb = ttk.Scrollbar(mcf, orient='vertical', command=self.mc.interior.yview)
        self.mc.interior.configure(yscrollcommand=ysb.set)
        ysb.pack(fill=tk.BOTH, expand=0, side=tk.RIGHT)
        xsb = ttk.Scrollbar(mcf, orient='horizontal', command=self.mc.interior.xview)
        self.mc.interior.configure(xscrollcommand=xsb.set)
        xsb.pack(fill=tk.BOTH, expand=0, side=tk.BOTTOM)
        # place
        self.mc.interior.pack(fill=tk.BOTH, expand=1, side=tk.TOP, padx=0, pady=0)
        self.mc.fit_width_to_content()

        # buttons
        mcbf = ttk.Frame(self)
        mcbf.pack(fill=tk.BOTH, expand=0, side=tk.TOP, padx=0, pady=0)
        remove_selected_files_button = ttk.Button(mcbf, text='Remove Files', command=self._remove_selected_files)
        remove_selected_files_button.pack(expand=0, side=tk.RIGHT, padx=3, pady=3)
        open_button = ttk.Button(mcbf, text='Add Files', command=self._selectFiles)
        open_button.pack(expand=0, side=tk.RIGHT, padx=3, pady=3)
        sort_button = ttk.Button(mcbf, text='Sort', command=self.sort_tfiles)
        sort_button.pack(expand=0, side=tk.LEFT, padx=3, pady=3)

        ## Station priority 
        self.station_priority_frame = ttk.LabelFrame(self, text='Station Priority')
        self.station_priority_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=0, padx=3, pady=3)
        self.stations_priority_lbs = []
        
    def update_stations(self):
        tmp = [ x[1]['station'] for x in self.tfiles.items() ]
        stations = []
        for x in tmp:
            if x not in stations:
                stations.append(x)
        print(stations)
        # @TCC should preserve selections already made if possible
        self.stations = stations

        for lb in self.stations_priority_lbs:
            lb.destroy()
        self.stations_priority_lbs = [] 
        for i,station in enumerate(self.stations):
            lb = ttk.Combobox(self.station_priority_frame, state="readonly",
                              values=self.stations[i:],
                              exportselection=0)
            lb.set(self.stations[i])
            lb.pack(side=tk.LEFT, padx=3, pady=3)
            self.stations_priority_lbs.append(lb)

            
    def _selectFiles(self):
        selected_files = tk.filedialog.askopenfilenames(
                                parent=self.root,
                                title='Choose Temperature Files',
                                filetypes=(("CSV files","*.csv"),("all files","*.*")))                               
        self.update_selected_files(selected_files, replace=False)
        
    def update_tfiles_listbox(self):
        # update the multicolumn_listbox
        self.selected_files_strvar.set(str(self.tfiles.keys()))
        self.mc.clear()
        for fn, tfile in self.tfiles.items():
            # note: filename is assumed to be the last element by _remove_selected_files
            self.mc.insert_row([tfile['station'], 
                                tfile['df'].index[0],
                                tfile['df'].index[-1],
                                tfile['df'].shape[0],
                                fn])#, index=self.mc.number_of_rows)
        self.mc.fit_width_to_content()

    def _on_select(self, data):
        # called when a multicolumn_listbox row is selected
        pass

    def _remove_selected_files(self):
        for row in self.mc.selected_rows:
            del self.tfiles[row[-1]]
        self.mc.delete_all_selected_rows()
        
    def update_selected_files(self, selected_files, replace=False):
        if replace:
            self.tfiles = ordereddict()
        for i,fn in enumerate(selected_files):
            if fn not in self.tfiles:
                print("Loading", fn)
                df = pd.read_csv(fn, parse_dates=['Date']).dropna()
                tcol = [x for x in df.columns if x.startswith('Temperature ')]
                if len(tcol) < 1:
                    print("ERROR: Temperature column not found", file=sts.stderr)
                else:
                    tmp = [x.strip() for x in tcol[0].split(',')]
                    station = tmp[-1]                   
                    t = df.loc[:,['Date',tcol[0]]]
                    t.set_index('Date', inplace=True)
                    t.columns = ['temperature']
                    t.sort_index(inplace=True)
                    #t['station'] = station
                    first = t.index[0]
                    last = t.index[-1]
                    self.tfiles[fn] = dict()
                    self.tfiles[fn]['df'] = t                
                    self.tfiles[fn]['station'] = station
                    self.tfiles[fn]['tcol'] = tcol[0]
        self.sort_tfiles()
        self.update_stations()

    def sort_tfiles(self):
        # sort by station, first date, last date
        self.tfiles = ordereddict(sorted(self.tfiles.items(), 
                                    key=lambda x: (x[1]['df'].index[-1], 
                                                   x[1]['df'].index[0],
                                                   x[1]['station'])))
        print(*list(self.tfiles.keys()), sep='\n')
        self.update_tfiles_listbox()


if __name__ == '__main__':
    root = tk.Tk()
    #root.geometry("800x600")
    app = App(root)
    root.mainloop()

