#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import tkinter.filedialog
from multicolumn_listbox import Multicolumn_Listbox

import numpy as np


class App(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.selected_files = []
        self.selected_files_strvar = tk.StringVar()
        self.root.title("DD Tool")
        self.pack(fill=tk.BOTH, expand=1)

        # Temperature files area
        foo = ttk.Label(self, text='Temperature Data Files', font='fixed 14 bold')
        foo.pack(fill=tk.X, expand=0, padx=3, pady=3)

        # multicolumn listbox widget
        self.mc = Multicolumn_Listbox(self, ["column one","column two", "column three"],
                stripped_rows = ("white","#f2f2f2"),
                command=self._on_select,
                adjust_heading_to_content=True,
                cell_anchor="center")
        # scrollbars
        ysb = ttk.Scrollbar(self.mc.interior, orient='vertical', command=self.mc.interior.yview)
        self.mc.interior.configure(yscrollcommand=ysb.set)
        ysb.pack(fill=tk.BOTH, expand=0, side=tk.RIGHT)
        xsb = ttk.Scrollbar(self.mc.interior, orient='horizontal', command=self.mc.interior.xview)
        self.mc.interior.configure(xscrollcommand=xsb.set)
        xsb.pack(fill=tk.BOTH, expand=0, side=tk.BOTTOM)
        # place
        self.mc.interior.pack(fill=tk.BOTH, expand=1, side=tk.TOP, padx=3, pady=3)
        self.mc.fit_width_to_content()

        self.open_button = ttk.Button(self, text='Select Files', command=self._selectFiles)
        self.open_button.pack(expand=0, side=tk.RIGHT, padx=3, pady=3)

        #self.tree = ttk.Treeview(frame_left, show='tree')
        #ysb = ttk.Scrollbar(frame_left, orient='vertical', command=self.tree.yview)
        #xsb = ttk.Scrollbar(frame_left, orient='horizontal', command=self.tree.xview)
        ## right-side
        #frame_right = tk.Frame(splitter)
        #nb = ttk.Notebook(frame_right)
        #page1 = ttk.Frame(nb)
        #page2 = ttk.Frame(nb)
        #text = ScrolledText(page2)

        ## overall layout
        #splitter.add(frame_left)
        #splitter.add(frame_right)
        #splitter.pack(fill=tk.BOTH, expand=1)
        ## left-side widget layout
        #self.tree.grid(row=0, column=0, sticky='NSEW')
        #ysb.grid(row=0, column=1, sticky='ns')
        #xsb.grid(row=1, column=0, sticky='ew')
        ## left-side frame's grid config
        ##frame_left.columnconfigure(0, weight=1)
        #frame_left.rowconfigure(0, weight=1)
        ## right-side widget layout
        #text.pack(expand=1, fill="both")
        #nb.add(page1, text='One')
        #nb.add(page2, text='Two')
        #nb.pack(expand=1, fill="both")

        ## setup
        #self.tree.configure(yscrollcommand=lambda f, l:self.autoscroll(ysb,f,l), xscrollcommand=lambda f, l:self.autoscroll(xsb,f,l))
        ## use this line instead of the previous, if you want the scroll bars to always be present, but grey-out when uneeded instead of disappearing
        ## self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        #self.tree.heading('#0', text='Project tree', anchor='w')
        #self.tree.column("#0",minwidth=1080, stretch=True)
        ## add default tree node
        #abspath = os.path.abspath(path)
        #self.nodes = dict()
        #self.insert_node('', abspath, abspath)
        #self.tree.bind('<<TreeviewOpen>>', self.open_node)

    def autoscroll(self, sbar, first, last):
        """Hide and show scrollbar as needed."""
        first, last = float(first), float(last)
        if first <= 0 and last >= 1:
            sbar.pack_forget()
        else:
            sbar.pack()
        sbar.set(first, last)

    def _selectFiles(self):
        self.selected_files = tk.filedialog.askopenfilenames(
                                parent=self.root,
                                title='Choose Temperature Files')
        self.selected_files_strvar.set(str(self.selected_files))
        #self.mc.table_data = np.random.randint(0,1000, size=(20,3)).tolist()
        self.mc.clear()
        for i,fn in enumerate(self.selected_files):
            self.mc.insert_row([str(i), "FOO", fn])
        self.mc.fit_width_to_content()

    def _on_select(self, data):
        print("called command when row is selected")
        print(data)



if __name__ == '__main__':
    root = tk.Tk()
    #root.geometry("800x600")
    app = App(root)
    root.mainloop()

