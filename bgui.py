#!/usr/bin/env python

# top-level launch script for the BCMD GUI

import sys
import Tkinter as tk

# components that do the actual work
import bgui.Config
import bgui.MainWindow

APP_STATE = {}

# ensure that configuration is synced before saving
def cleanup():
    APP_STATE['app'].sync_to_config()
    root.destroy()

# configure and run
if __name__ == '__main__':
    config = bgui.Config.Config(sys.argv)
    if config:
        root = tk.Tk()
        root.title('BCMD')
        root.protocol('WM_DELETE_WINDOW', cleanup)
        app = bgui.MainWindow.MainWindow(root, config)
        
        APP_STATE['app'] = app
        APP_STATE['root'] = root
        APP_STATE['config'] = config
        
        if app:
            app.mainloop()
            config.save()
