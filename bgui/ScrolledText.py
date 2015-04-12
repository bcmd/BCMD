#!/usr/bin/python

import Tkinter as tk
import ttk

PADDING=6

class ScrolledText(tk.Frame):
    
    def __init__(self, parent, wrap='word', autogrid=True, highlightthickness=0, **kwargs):
        tk.Frame.__init__(self, parent, padx=PADDING, pady=PADDING, **kwargs)
        if autogrid:
            self.grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))
            parent.columnconfigure(1, weight=1)
            parent.rowconfigure(1, weight=1)
        tk.Frame.columnconfigure(self, 1, weight=1)
        tk.Frame.rowconfigure(self, 1, weight=1)
        
        self.yscroller = ttk.Scrollbar(self, orient=tk.VERTICAL, **kwargs)
        self.textarea = tk.Text(self, wrap=wrap, yscrollcommand=self.yscroller.set,
                                highlightthickness=highlightthickness, **kwargs)
        self.yscroller.config(command=self.textarea.yview)
                
        self.yscroller.grid(row=1, column=2, sticky=(tk.N, tk.E, tk.S))
        self.textarea.grid(row=1, column=1, sticky=(tk.W, tk.N, tk.E, tk.S))
        
        if wrap=='none':
            self.xscroller = ttk.Scrollbar(self, orient=tk.HORIZONTAL, **kwargs)
            self.textarea.config(xscrollcommand=self.xscroller.set)
            self.xscroller.config(command=self.textarea.xview)
            self.xscroller.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.S))
    
    def setText(self, text):
        self.textarea.delete(1.0, tk.END)
        self.textarea.insert(1.0, text)
    
    def log(self, text, newline=True):
        self.textarea.insert(tk.END, text)
        if newline:
            self.textarea.insert(tk.END, '\n')
    
    def fromFile(self, filename):
        with open(filename, 'r') as f:
            self.setText(f.read())
    
    def getText(self):
        self.textarea.get(1.0, tk.END)


# simple test driver
if __name__ == '__main__':
    root = tk.Tk()
    scroller = ScrolledText(root, autogrid=True, wrap='none')
    
    filler = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras tempus iaculis est, sagittis facilisis urna. Cras est orci, posuere eget
dolor ullamcorper, lobortis volutpat massa. Phasellus convallis elementum neque, posuere scelerisque nisl tincidunt sed. Cras sagittis malesuada augue
vitae tempor. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Curabitur volutpat viverra neque, eu posuere ligula
eleifend vel. Proin id quam nisl. Donec et ornare mauris. Pellentesque mi lorem, elementum vitae magna quis, bibendum consequat mauris.

    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris ultrices euismod vehicula. Vivamus sed nulla nec sem varius ullamcorper eget vel sapien.
Aenean pulvinar nibh sit amet placerat hendrerit. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Cras cursus turpis
eget urna vulputate pharetra. Cras magna neque, consectetur ut dui ut, sodales lobortis ligula. Duis vitae accumsan mauris. Phasellus eu lorem velit. In aliquet
mollis tortor et cursus.

    Curabitur eleifend pretium dolor, id egestas risus eleifend non. Morbi egestas, neque non sollicitudin sodales, sapien orci sodales lectus, ullamcorper
venenatis nulla lectus nec justo. Sed ornare enim ac euismod dapibus. Praesent ipsum diam, congue sed dui vel, pharetra condimentum risus. Vivamus sem erat,
viverra vitae vestibulum id, elementum vel enim. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Suspendisse
potenti. Duis sollicitudin quam eu erat scelerisque auctor. In hac habitasse platea dictumst. Integer gravida mauris vitae pharetra dapibus.

    Duis sed orci vitae elit commodo eleifend vitae quis sapien. Phasellus condimentum neque non velit accumsan, ut imperdiet mi malesuada. Proin congue lectus
ut lacus scelerisque rutrum. Integer nibh nisl, aliquet varius semper at, venenatis in eros. Phasellus vel lectus est. Suspendisse tincidunt, mi at pulvinar
consequat, nisi orci congue odio, suscipit facilisis augue ante vel ligula. Aliquam sit amet massa sit amet urna cursus fringilla. Pellentesque et laoreet diam.
Ut bibendum quis magna non elementum.

    Aenean eu eleifend mi. Suspendisse potenti. Maecenas vulputate condimentum lorem, sit amet pretium eros ornare id. Phasellus dolor quam, faucibus non viverra
eu, viverra nec purus. Nam varius lacus eu ipsum imperdiet volutpat. Nullam a tristique orci. Donec ornare eget neque at aliquam. Nunc fermentum, orci et semper
interdum, mi ipsum eleifend tortor, sit amet sagittis augue ligula non tortor. Donec sem ipsum, tincidunt eget aliquam in, bibendum vitae ligula. Proin molestie
dolor a mi vulputate aliquam. Donec interdum lectus ut turpis ullamcorper, id bibendum tortor lacinia. Curabitur sit amet elit nisi. Suspendisse potenti. Nulla
consectetur purus ante, sed condimentum odio iaculis a. Nunc accumsan diam erat, vitae accumsan lacus sodales non. Morbi pellentesque arcu elit.'''

    scroller.setText(filler)
    root.mainloop()
