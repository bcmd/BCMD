# Dialog for specifying simple plot details
import Tkinter as tk
import ttk

from Dialog import Dialog

class AxisChooser(Dialog):
    
    def __init__(self, parent, fields=[], title=None):
        self.fields = sorted(fields, key=str.lower)
        Dialog.__init__(self, parent, title)
    
    def body(self, master):
        
        self.combo_x = ttk.Combobox(master, values=self.fields)
        self.combo_y = ttk.Combobox(master, values=self.fields)
        
        ttk.Label(master, text='Y axis').grid(column=1, row=1, sticky=tk.W)
        self.combo_y.grid(row=2,column=1,sticky=(tk.N, tk.W, tk.E, tk.S))        
        ttk.Label(master, text='X axis').grid(column=1, row=3, sticky=tk.W)
        self.combo_x.grid(row=4,column=1,sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.typeVar = tk.StringVar()
        self.typeVar.set('-')
        self.lineButton = ttk.Radiobutton(master, text='Line', variable=self.typeVar, value='-')
        self.pointsButton = ttk.Radiobutton(master, text='Scatter', variable=self.typeVar, value='o')

        self.lineButton.grid(column=1, row=5, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.pointsButton.grid(column=1, row=6, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        return self.combo_y # initial focus


    def apply(self):
        self.result = { 'x' : self.combo_x.get(),
                        'y' : self.combo_y.get(),
                        'type' : self.typeVar.get() }
