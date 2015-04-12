#!/usr/bin/env python

import sys, os, os.path

import Tkinter as tk
import ttk

import matplotlib
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class SimplePlot(tk.Frame):

    def __init__(self, parent, autogrid=True, figsize=(6, 4)):
        tk.Frame.__init__(self, parent)
        if autogrid:
            self.grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))
            parent.columnconfigure(1, weight=1)
            parent.rowconfigure(1, weight=1)
        tk.Frame.columnconfigure(self, 1, weight=1)
        tk.Frame.rowconfigure(self, 1, weight=1)
        
        self.figure = Figure(figsize=figsize, facecolor='w')
        self.subplot = self.figure.add_subplot(1,1,1)
        self.subplot.margins(0.05, 0.05)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))

# simple test driver
if __name__ == '__main__':
    root = tk.Tk()
    root.title('SimplePlot test')
    plotter = SimplePlot(root)
    plotter.subplot.plot([1,2,3,4,5],[1,4,9,16,25])
    
    root.mainloop()
