#!/usr/bin/python

import Tkinter as tk
import ttk
import sys, os, os.path

PADDING=0

class ScrolledImage(tk.Frame):
    
    def __init__(self, parent, autogrid=True, highlightthickness=0, **kwargs):
        tk.Frame.__init__(self, parent, padx=PADDING, pady=PADDING, **kwargs)
        if autogrid:
            self.grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))
            parent.columnconfigure(1, weight=1)
            parent.rowconfigure(1, weight=1)
        tk.Frame.columnconfigure(self, 1, weight=1)
        tk.Frame.rowconfigure(self, 1, weight=1)
        
        self.yscroller = ttk.Scrollbar(self, orient=tk.VERTICAL, **kwargs)
        self.xscroller = ttk.Scrollbar(self, orient=tk.HORIZONTAL, **kwargs)
        self.canvas = tk.Canvas(self, yscrollcommand=self.yscroller.set,
                                xscrollcommand=self.xscroller.set,
                                highlightthickness=highlightthickness, **kwargs)
        self.yscroller.config(command=self.canvas.yview)
        self.xscroller.config(command=self.canvas.xview)
                
        self.yscroller.grid(row=1, column=2, sticky=(tk.N, tk.E, tk.S))        
        self.xscroller.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.S))
        self.canvas.grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))
        
        self.image = None
        
    def setImage(self, image):
        self.image = image
        self.canvas.config(scrollregion=(0, 0, image.width(), image.height()))
        self.canvas.create_image(0, 0, anchor='nw', image=self.image)
    
    def fromFile(self, filename):
        self.setImage(tk.PhotoImage(file=filename))
    
    def getImage(self):
        return self.image


# simple test driver -- open with image file specified as command-line arg
if __name__ == '__main__':
    root = tk.Tk()
    scroller = ScrolledImage(root, autogrid=True)
    scroller.fromFile(sys.argv[1])
    root.mainloop()
