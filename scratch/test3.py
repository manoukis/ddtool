import os
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

class App(object):
    def __init__(self, master, path):
        splitter = tk.PanedWindow(master, orient=tk.HORIZONTAL)
        # left-side
        frame_left = tk.Frame(splitter)
        self.tree = ttk.Treeview(frame_left, show='tree')
        ysb = ttk.Scrollbar(frame_left, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(frame_left, orient='horizontal', command=self.tree.xview)
        # right-side
        frame_right = tk.Frame(splitter)
        nb = ttk.Notebook(frame_right)
        page1 = ttk.Frame(nb)
        page2 = ttk.Frame(nb)
        text = ScrolledText(page2)

        # overall layout
        splitter.add(frame_left)
        splitter.add(frame_right)
        splitter.pack(fill=tk.BOTH, expand=1)
        # left-side widget layout
        self.tree.grid(row=0, column=0, sticky='NSEW')
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')
        # left-side frame's grid config
        frame_left.columnconfigure(0, weight=1)
        frame_left.rowconfigure(0, weight=1)
        # right-side widget layout
        text.pack(expand=1, fill="both")
        nb.add(page1, text='One')
        nb.add(page2, text='Two')
        nb.pack(expand=1, fill="both")

        # setup
        self.tree.configure(yscrollcommand=lambda f, l:self.autoscroll(ysb,f,l), xscrollcommand=lambda f, l:self.autoscroll(xsb,f,l))
        # use this line instead of the previous, if you want the scroll bars to always be present, but grey-out when uneeded instead of disappearing
        # self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.tree.heading('#0', text='Project tree', anchor='w')
        self.tree.column("#0",minwidth=1080, stretch=True)
        # add default tree node
        abspath = os.path.abspath(path)
        self.nodes = dict()
        self.insert_node('', abspath, abspath)
        self.tree.bind('<<TreeviewOpen>>', self.open_node)

    def autoscroll(self, sbar, first, last):
        """Hide and show scrollbar as needed."""
        first, last = float(first), float(last)
        if first <= 0 and last >= 1:
            sbar.grid_remove()
        else:
            sbar.grid()
        sbar.set(first, last)

    def insert_node(self, parent, text, abspath):
        node = self.tree.insert(parent, 'end', text=text, open=False)
        if os.path.isdir(abspath):
            self.nodes[node] = abspath
            self.tree.insert(node, 'end')

    def open_node(self, event):
        node = self.tree.focus()
        abspath = self.nodes.pop(node, None)
        if abspath:
            self.tree.delete(self.tree.get_children(node))
            for p in os.listdir(abspath):
                self.insert_node(node, p, os.path.join(abspath, p))


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("800x600")
    app = App(root, path='.')
    root.mainloop()

