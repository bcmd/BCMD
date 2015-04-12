#!/usr/bin/python

# main application interface window for the BCMD GUI

import sys, os, os.path
import decimal
import numpy as np

import Tkinter as tk
import ttk
import tkFileDialog

# local helper components
import ScrolledText as stxt
import ScrolledImage as simg
import SimplePlot as splt
import AxisChooser as chx
import Executor
import Validator
import Config

import batch.inputs as inputs
import bparser.info as info
import bparser.doc_html as doc_html
import bparser.doc_latex as doc_latex
import bparser.doc_modeldef as doc_modeldef
import bparser.doc_sbml as doc_sbml
import batch.siggen as siggen

# notes to self:
#
# options['defaultextension'] = '.txt'
# options['filetypes'] = [('all files', '.*'), ('text files', '.txt')]
# options['initialdir'] = 'C:\\'
# options['initialfile'] = 'myfile.txt'
# options['parent'] = root
# options['title'] = 'This is a title'
#
# This is only available on the Macintosh, and only when Navigation Services are installed.
# options['message'] = 'message'
#
# if you use the multiple file version of the module functions this option is set automatically.
# options['multiple'] = 1
#
# defining options for opening a directory
# self.dir_opt = options = {}
# options['initialdir'] = 'C:\\'
# options['mustexist'] = False
# options['parent'] = root
# options['title'] = 'This is a title'
#
# dirname = tkFileDialog.askdirectory(**options)
# filename = tkFileDialog.askopenfilename(**options)
# filename = tkFileDialog.asksaveasfilename(**options)

class MainWindow(ttk.Frame):

    # construction
    def __init__(self, parent, config, autogrid=True, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.config = config
        
        self.floaters = {}
        
        if autogrid:
            parent.columnconfigure(1, weight=1)
            parent.rowconfigure(1, weight=1)
            self.grid(row=1, column=1, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        # apportion stretchiness
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.initialise_variables()
        self.layout_UI()
        
        # do any post-layout layout and display
        self.finish_initing()
        
    # initialise tk variables for communicating with widgets
    def initialise_variables(self):
        # main pane
        self.model_name = tk.StringVar()
        self.input_name = tk.StringVar()
        self.coarse_name = tk.StringVar()
        self.detail_name = tk.StringVar()
                
        self.debug_state = tk.IntVar()
        self.match_state = tk.IntVar()
        self.coarse_state = tk.IntVar()
        self.detail_state = tk.IntVar()
        
        # input management pane
        self.generate_name = tk.StringVar()
        self.use_generated_state = tk.IntVar()
        
        # info pane
        self.graph_init_state = tk.IntVar()
        self.graph_unused_state = tk.IntVar()
        self.graph_params_state = tk.IntVar()
        self.graph_cluster_state = tk.IntVar()
        self.graph_LR_state = tk.IntVar()

        self.doc_tabular_state = tk.IntVar()
        self.doc_display_state = tk.IntVar()
        self.doc_align_state = tk.IntVar()
        
        self.export_derived_state = tk.IntVar()
        
        # inputs pane
        self.param_file_state = tk.IntVar()
        self.param_explicit_state = tk.IntVar()
        self.param_steady_state = tk.IntVar()
        self.param_omit_state = tk.IntVar()
        self.param_file_name = tk.StringVar()
        self.param_value = tk.StringVar()
        self.param_steady_duration = tk.StringVar()
        
        self.time_radio_state = tk.IntVar()
        self.time_file_name = tk.StringVar()
        self.time_rate = tk.StringVar()
        self.time_duration = tk.StringVar()
        self.time_priority_state = tk.IntVar()
        self.data_file_name = tk.StringVar()
        self.data_source_state = tk.IntVar()
        self.data_file_same_state = tk.IntVar()
        
        self.output_header_state = tk.IntVar()
        self.output_radio_state = tk.IntVar()
        self.output_omit_state = tk.IntVar()
        
        self.sync_from_config()
        
        # additional transient (ie, non-config) variables
        self.parsed_model = None
        self.file_params = {}
        self.explicit_params = {}
        self.explicit_outputs = []
        self.signals = {}
        self.time_contents = {}
        self.data_contents = {}
        
        self.data_scale = tk.StringVar()
        self.data_offset = tk.StringVar()
        self.data_min = tk.StringVar()
        self.data_max = tk.StringVar()
        self.data_stretch = tk.StringVar()
        self.reset_preset_adjustments()

    # default values for the synth post-proc adjustments
    # this is all just a hack until proper preset editing is implemented
    def reset_preset_adjustments(self):
        self.data_scale.set('1')
        self.data_offset.set('0')
        self.data_min.set('')
        self.data_max.set('')
        self.data_stretch.set('')
    
    # layout the UI elements
    def layout_UI(self):
        self.top_level = ttk.Notebook(self)
        self.top_level.grid(column=1, row=1, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        # build the individual panes and add them to the notebook
        self.add_model_panel()
        self.add_info_panel()
        self.add_input_panel()
        #self.add_optim_panel()
        #self.add_abc_panel()
    
    # miscellaneous finalising and tidying before getting interactive
    def finish_initing(self):
        try:
            self.action_parse_info()
        except:
            pass
        
        if self.config.param_file and self.config.use_param_file:
            self.load_param_vals()
        else:
            self.show_initial_values()
        
        self.show_output_fields()
        
        if self.config.time_file:
            self.load_time_file()
        
        if self.config.data_file and not self.config.shared_data_file:
            self.load_data_file()
        
        self.show_signals()
        
    
    # main pane provides and interface to build and run models given existing definitions and inputs
    def add_model_panel(self):
        
        self.model_panel = ttk.Frame(self.top_level)
        self.model_panel.columnconfigure(1, weight=1)
        self.model_panel.rowconfigure(11, weight=1)
   
        self.model_field = ttk.Entry(self.model_panel, width=10, textvariable=self.model_name)
        self.input_field = ttk.Entry(self.model_panel, width=10, textvariable=self.input_name)
        self.coarse_field = ttk.Entry(self.model_panel, width=10, textvariable=self.coarse_name)
        self.detail_field = ttk.Entry(self.model_panel, width=10, textvariable=self.detail_name)
    
        self.model_field.grid(column=1, row=2, sticky=(tk.E,tk.W))
        self.input_field.grid(column=1, row=4, sticky=(tk.E,tk.W))
        self.coarse_field.grid(column=1, row=8, sticky=(tk.E,tk.W))
        self.detail_field.grid(column=1, row=10, sticky=(tk.E,tk.W))
    
        ttk.Label(self.model_panel, text='Model').grid(column=1, row=1, sticky=tk.W)
        ttk.Label(self.model_panel, text='Input').grid(column=1, row=3, sticky=tk.W)
        ttk.Label(self.model_panel, text='Outputs').grid(column=1, row=6, sticky=tk.W)
    
        ttk.Button(self.model_panel, text='Build', command=self.action_build).grid(column=3, row=2, sticky=tk.W)
        ttk.Button(self.model_panel, text='Run', command=self.action_run).grid(column=3, row=4, sticky=tk.W)
        
        ttk.Button(self.model_panel, text='Open', command=self.action_open_coarse).grid(column=3, row=8, sticky=tk.W)
        ttk.Button(self.model_panel, text='Open', command=self.action_open_detail).grid(column=3, row=10, sticky=tk.W)
        
        ttk.Button(self.model_panel, text='Plot', command=self.action_plot_coarse).grid(column=4, row=8, sticky=tk.W)
        ttk.Button(self.model_panel, text='Plot', command=self.action_plot_detail).grid(column=4, row=10, sticky=tk.W)
    
        self.debug_check = ttk.Checkbutton(self.model_panel, text='Debug', variable=self.debug_state)
        self.match_check = ttk.Checkbutton(self.model_panel, text='As Model', variable=self.match_state)
        self.coarse_check = ttk.Checkbutton(self.model_panel, text='Coarse', variable=self.coarse_state)
        self.detail_check = ttk.Checkbutton(self.model_panel, text='Detailed', variable=self.detail_state)
    
        self.debug_check.grid(column=4, row=2, sticky=tk.W)
        self.match_check.grid(column=4, row=4, sticky=tk.W)
        
        self.coarse_check.grid(column=1, row=7, sticky=tk.W)
        self.detail_check.grid(column=1, row=9, sticky=tk.W)
    
        self.load_icon = tk.PhotoImage(file=os.path.join(self.config.resources, 'files-blue.gif'))
        ttk.Button(self.model_panel, image=self.load_icon, command=self.action_choose_model).grid(column=2, row=2, sticky=tk.W)
        ttk.Button(self.model_panel, image=self.load_icon, command=self.action_choose_input).grid(column=2, row=4, sticky=tk.W)
    
        self.logs = ttk.Notebook(self.model_panel)
        self.app_log = stxt.ScrolledText(self.logs, autogrid=False)
        self.build_log = stxt.ScrolledText(self.logs, autogrid=False, wrap='none')
        self.stdout_log = stxt.ScrolledText(self.logs, autogrid=False)
        self.stderr_log = stxt.ScrolledText(self.logs, autogrid=False)
        self.logs.add(self.app_log, text='Messages')
        self.logs.add(self.build_log, text='Build Log')
        self.logs.add(self.stdout_log, text='StdOut')
        self.logs.add(self.stderr_log, text='StdErr')
    
        self.logs.grid(row=11, column=1, columnspan=4, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.top_level.add(self.model_panel, text='Model')
        
        
    def add_input_panel(self):
        self.input_panel = ttk.Frame(self.top_level)
        self.input_panel.columnconfigure(1, weight=1)
        self.input_panel.rowconfigure(4, weight=1)
        
        self.generate_field = ttk.Entry(self.input_panel, width=10, textvariable=self.generate_name)
        self.generate_field.bind('<Return>', self.action_generate)
        self.generate_field.grid(column=1, row=2, sticky=(tk.E,tk.W))
        
        ttk.Label(self.input_panel, text='File').grid(column=1, row=1, sticky=tk.W)
        ttk.Button(self.input_panel, image=self.load_icon, command=self.action_choose_generate_dir).grid(column=2, row=2, sticky=tk.W)
        ttk.Button(self.input_panel, text='Generate', command=self.action_generate).grid(column=3, row=2, sticky=tk.W)
        
        self.use_generated_check = ttk.Checkbutton(self.input_panel, text='Set Input', variable=self.use_generated_state)
        self.use_generated_check.grid(column=4, row=2, sticky=tk.W)
        
        self.sections = ttk.Notebook(self.input_panel)
        self.add_param_section()
        self.add_signals_section()
        self.add_output_section()        
        self.sections.grid(row=4, column=1, columnspan=4, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.top_level.add(self.input_panel, text='Control')
    
    def add_param_section(self):
        self.param_section = ttk.Frame(self.sections)
        
        self.param_file_check = ttk.Checkbutton(self.param_section, text='From File', variable=self.param_file_state, command=self.show_initial_values)
        self.param_explicit_check = ttk.Checkbutton(self.param_section, text='Explicit', variable=self.param_explicit_state, command=self.show_initial_values)
        self.param_steady_check = ttk.Checkbutton(self.param_section, text='Equilibrate', variable=self.param_steady_state)
        self.param_omit_check = ttk.Checkbutton(self.param_section, text='Model Only', variable=self.param_omit_state, command=self.show_initial_values)        
        self.param_file_field = ttk.Entry(self.param_section, width=10, textvariable=self.param_file_name)
        self.param_steady_duration_field = ttk.Entry(self.param_section, width=10, textvariable=self.param_steady_duration)
        self.param_value_field = ttk.Entry(self.param_section, width=10, textvariable=self.param_value)
        self.param_value_field.bind('<Return>', self.param_value_field_do)
        self.param_field_combo = ttk.Combobox(self.param_section, values=[])
        self.param_field_combo.bind('<<ComboboxSelected>>', self.param_field_combo_validate)
        self.param_textarea = stxt.ScrolledText(self.param_section, autogrid=False)
        
        self.param_section.columnconfigure(2, weight=1)
        self.param_section.rowconfigure(7, weight=1)
        self.param_file_check.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        self.param_file_field.grid(column=1, row=2, columnspan=2, sticky=(tk.E,tk.W))
        ttk.Button(self.param_section, image=self.load_icon, command=self.action_choose_param_file).grid(column=3, row=2, sticky=(tk.W, tk.E))
        self.param_omit_check.grid(row=2, column=4, columnspan=3, sticky=tk.W)
        self.param_explicit_check.grid(row=3, column=1, columnspan=2, sticky=tk.W)
        self.param_field_combo.grid(row=4, column=1, columnspan=2, sticky=(tk.E, tk.W))
        self.param_value_field.grid(row=4, column=3, sticky=(tk.E, tk.W))
        ttk.Button(self.param_section, text='+', width=1, command=self.action_add_explicit).grid(row=4, column=4, sticky=tk.W)
        ttk.Button(self.param_section, text='-', width=1, command=self.action_remove_explicit).grid(row=4, column=5, sticky=tk.W)
        ttk.Button(self.param_section, text='Clear', width=4, command=self.action_clear_all_explicits).grid(row=4, column=6, sticky=tk.W)
        self.param_steady_check.grid(row=5, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(self.param_section, text='Duration').grid(column=1, row=6, sticky=tk.W)
        self.param_steady_duration_field.grid(row=6, column=2, sticky=(tk.E, tk.W))
        self.param_textarea.grid(row=7, column=1, columnspan=6, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.sections.add(self.param_section, text="Initial Values")

    def param_value_field_do(self, args):
        if self.param_value_field.get().strip() == '':
            self.action_remove_explicit()
        else:
            self.action_add_explicit()
        return None
    
    def param_field_combo_validate(self, args):
        if self.param_field_combo.get().startswith('-'):
            self.param_field_combo.set('')
        return None

    def data_field_combo_validate(self, args):
        if self.data_field_combo.get().startswith('-'):
            self.data_field_combo.set('')
        return None
    
    def add_signals_section(self):
        self.signals_section = ttk.Frame(self.sections)
        
        self.time_radio_file = ttk.Radiobutton(self.signals_section, text='From File', variable=self.time_radio_state, value=Config.TIME_FROM_FILE, command=self.show_signals)
        self.time_radio_specify = ttk.Radiobutton(self.signals_section, text='Specify', variable=self.time_radio_state, value=Config.TIME_SPECIFY, command=self.show_signals)
        self.time_file_field = ttk.Entry(self.signals_section, width=10, textvariable=self.time_file_name)
        self.time_file_combo =  ttk.Combobox(self.signals_section, state='readonly', values=[])
        self.time_rate_field = ttk.Entry(self.signals_section, width=10, textvariable=self.time_rate)
        self.time_duration_field = ttk.Entry(self.signals_section, width=10, textvariable=self.time_duration)
        self.time_radio_prioritise_data = ttk.Radiobutton(self.signals_section, text='Data Priority', state='disabled', variable=self.time_priority_state, value=Config.PRIORITISE_DATA, command=self.show_signals)
        self.time_radio_prioritise_time = ttk.Radiobutton(self.signals_section, text='Time Priority', state='disabled', variable=self.time_priority_state, value=Config.PRIORITISE_TIME, command=self.show_signals)
        self.time_file_combo.bind('<<ComboboxSelected>>', self.show_signals)
        self.time_rate_field.bind('<Return>', self.show_signals)
        self.time_duration_field.bind('<Return>', self.show_signals)

        self.data_file_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_file_name)
        self.data_file_column_combo =  ttk.Combobox(self.signals_section, state='readonly', values=[])
        self.data_field_combo =  ttk.Combobox(self.signals_section, values=[])
        self.data_synth_presets_combo = ttk.Combobox(self.signals_section, values=sorted(self.config.presets.keys(), key=str.lower), state='readonly')
        self.data_radio_file = ttk.Radiobutton(self.signals_section, text='From File', variable=self.data_source_state, value=Config.FILE_DATA, command=self.show_signals)
        self.data_radio_synth = ttk.Radiobutton(self.signals_section, text='Synthesize', variable=self.data_source_state, value=Config.SYNTH_DATA, command=self.show_signals)
        self.same_file_check = ttk.Checkbutton(self.signals_section, text='Same As Time', variable=self.data_file_same_state, command=self.sync_data_time)
        self.data_field_combo.bind('<<ComboboxSelected>>', self.data_field_combo_validate)
        
        self.data_scale_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_scale)
        self.data_offset_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_offset)
        self.data_min_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_min)
        self.data_max_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_max)
        self.data_stretch_field = ttk.Entry(self.signals_section, width=10, textvariable=self.data_stretch)
        
        self.signals_textarea = stxt.ScrolledText(self.signals_section, autogrid=False)

        self.signals_section.columnconfigure(2, weight=1)
        self.signals_section.rowconfigure(20, weight=1)
        
        ttk.Label(self.signals_section, text='Time Base').grid(column=1, row=1, columnspan=2, sticky=tk.W)
        self.time_radio_file.grid(column=1, row=2, columnspan=2, sticky=(tk.E,tk.W))
        self.time_file_field.grid(column=1, row=3, columnspan=2, sticky=(tk.E,tk.W))
        ttk.Button(self.signals_section, image=self.load_icon, command=self.action_choose_time_file).grid(column=3, row=3, sticky=(tk.W, tk.E))
        self.time_file_combo.grid(column=4, row=3, columnspan=2, stick=(tk.W,tk.E))
        self.time_radio_specify.grid(column=1, row=5, columnspan=2, stick=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Sample Rate').grid(column=1, row=6, sticky=tk.W)
        self.time_rate_field.grid(column=2, row=6, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text=' /t').grid(column=3, row=6, sticky=tk.W)
        #self.time_radio_prioritise_data.grid(row=6, column=4, columnspan=2, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Duration').grid(column=1, row=7, sticky=tk.W)
        self.time_duration_field.grid(column=2, row=7, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text=' t').grid(column=3, row=7, sticky=tk.W)
        #self.time_radio_prioritise_time.grid(row=7, column=4, columnspan=2, sticky=(tk.E,tk.W))
        
        ttk.Separator(self.signals_section, orient='horizontal').grid(row=8, column=1, columnspan=5, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Data').grid(column=1, row=9, columnspan=2, sticky=tk.W)
        
        ttk.Label(self.signals_section, text='Field').grid(column=1, row=10, sticky=tk.W)
        self.data_field_combo.grid(column=2, row=10, sticky=(tk.W,tk.E))
        ttk.Button(self.signals_section, text='+', width=1, command=self.action_add_signal).grid(row=10, column=3, sticky=(tk.W, tk.E))
        ttk.Button(self.signals_section, text='-', width=1, command=self.action_remove_signal).grid(row=10, column=4, sticky=(tk.W, tk.E))
        ttk.Button(self.signals_section, text='Clear', width=4, command=self.action_clear_all_signals).grid(row=10, column=5, sticky=(tk.W, tk.E))
        
        self.data_radio_file.grid(column=1, columnspan=2, row=11, sticky=tk.W)
        self.data_file_field.grid(column=1, columnspan=2, row=12, sticky=(tk.W,tk.E))
        ttk.Button(self.signals_section, image=self.load_icon, command=self.action_choose_data_file).grid(column=3, row=12, sticky=(tk.W, tk.E))
        self.same_file_check.grid(column=4, row=12, columnspan=2, sticky=tk.W)
        ttk.Label(self.signals_section, text='Column').grid(column=1, row=13, sticky=tk.W)
        self.data_file_column_combo.grid(column=2, row=13, sticky=(tk.W,tk.E))
        ttk.Button(self.signals_section, text='Filter...', state='disabled', command=self.action_define_filter).grid(row=13, column=4, columnspan=2, sticky=(tk.W,tk.E))

        self.data_radio_synth.grid(column=1, columnspan=2, row=14, sticky=tk.W)
        ttk.Label(self.signals_section, text='Preset').grid(column=1, row=15, sticky=tk.W)
        self.data_synth_presets_combo.grid(column=2, row=15, sticky=(tk.W,tk.E))
        ttk.Button(self.signals_section, text='Edit Presets...', state='disabled', command=self.action_edit_presets).grid(column=3, columnspan=2, row=15, sticky=(tk.W,tk.E))
        ttk.Label(self.signals_section, text='Scale').grid(column=1, row=16, sticky=tk.W)
        self.data_scale_field.grid(column=2, row=16, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Offset').grid(column=1, row=17, sticky=tk.W)
        self.data_offset_field.grid(column=2, row=17, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Min').grid(column=3, columnspan=1, row=16, sticky=tk.W)
        self.data_min_field.grid(column=4, columnspan=2, row=16, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Max').grid(column=3, columnspan=1, row=17, sticky=tk.W)
        self.data_max_field.grid(column=4, columnspan=2, row=17, sticky=(tk.E,tk.W))
        ttk.Label(self.signals_section, text='Speed').grid(column=1, row=18, sticky=tk.W)
        self.data_stretch_field.grid(column=2, row=18, sticky=(tk.E,tk.W))
        
        self.signals_textarea.grid(row=20, column=1, columnspan=5, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.sections.add(self.signals_section, text="Inputs")

    def show_signals(self, *args):
        self.sync_to_config()
        if self.config.time_from_file == Config.TIME_FROM_FILE:
            sigstr = 'Time from file %s, column "%s"\n' % (os.path.split(self.config.time_file)[1], self.time_file_combo.get())
        else:
            sigstr = 'Time: %g t @ %g/t -> %d steps of %g t\n' % (self.config.time_duration, self.config.time_rate,
                                                                  int(np.ceil(self.config.time_duration * self.config.time_rate)),
                                                                  1.0/self.config.time_rate)
        
        for field in sorted(self.signals.keys(), key=str.lower):
            spec = self.signals[field]
            if spec['kind'] == 'file':
                if self.config.shared_data_file:
                    sigstr = sigstr + '%s: column "%s" from file %s\n' % (field, spec['column'], os.path.split(self.config.time_file)[1])
                else:
                    sigstr = sigstr + '%s: column "%s" from file %s\n' % (field, spec['column'], os.path.split(spec['path'])[1])
            else:
                sigstr = sigstr + '%s: synth from preset "%s" * %g + %g -> [%g,%g] << %g\n' % (field, spec['preset'], spec['scale'], spec['offset'], spec['min'], spec['max'], spec['stretch'])
        
        self.signals_textarea.setText(sigstr)
    
    # collect/synthesize timebase and signal data
    def marshal_signals(self):
        mn = 1e15
        mx = 0
        # generate/import time
        if self.config.time_from_file == Config.TIME_FROM_FILE:
            # TODO: guard against obvious errors and do something sensible if this fails
            # for the moment we just assume there are multiple points and they are valid numbers
            start = np.array(self.time_contents.get(self.time_file_combo.get(), [0.0]), dtype=np.float_)
            end = np.append(start[1:], 2 * start[-1] - start[-2])
        else:
            start = np.arange(int(np.ceil(self.config.time_duration * self.config.time_rate)), dtype=np.float_)/self.config.time_rate
            end = start + 1/self.config.time_rate
        
        if len(start) > mx: mx = len(start)
        if len(start) < mn: mn = len(start)
        
        signals = {}
        for field in self.signals.keys():
            spec = self.signals[field]
            if spec['kind'] == 'file':
                if self.config.shared_data_file:
                    filedata = self.time_contents
                else:
                    # we support merging from multiple files, but in most cases the current one will be it
                    if spec['path'] == self.config.data_file:
                        filedata = self.data_contents
                    else:
                        filedata = inputs.readCSV(spec['path'], wrap_timeseries=False)
                signals[field] = filedata.get(spec['column'], [0.0])
            else:
                signals[field] = siggen.waves(start * spec['stretch'], self.config.presets[spec['preset']]) * spec['scale'] + spec['offset']
                signals[field] = np.clip(signals[field], spec['min'], spec['max'])
            
            if len(signals[field]) > mx: mx = len(signals[field])
            if len(signals[field]) < mn: mn = len(signals[field])
        
        # conform lengths
        # TODO: allow policy choices for this
        if mn != mx:
            # for the moment, just crop to the shortest signal
            # however, we will special-case zero length because we want there always to
            # *be* a signal
            if mn == 0:
                start = [0]
                end = [1]
                for field in signals.keys():
                    if len(signals[field]) > 0:
                        signals[field] = [signals[field][0]]
                    else:
                        signals[field] = [0]
            else:
                start = start[:mn]
                end = end[:mn]
                for field in signals.keys():
                    signals[field] = signals[field][:mn]
            
        return {'start':start, 'end':end }, signals
    
    def sync_data_time(self):
        self.sync_to_config()
        
        # if we've just ticked the box, copy time file name to data
        if self.config.shared_data_file:
            self.config.data_file = self.config.time_file
            self.sync_from_config()
    
    def action_add_signal(self):
        self.sync_to_config()
        
        # require the ID to be valid
        namestr = self.data_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.data_field_combo.set(namestr)
        else:
            self.bell()
            self.data_field_combo.set('')
            return
        
        if self.data_source_state.get() == Config.FILE_DATA:
            if self.config.data_file and self.data_file_column_combo.get():
                signal_spec = { 'kind':'file',
                                'path':self.config.data_file,
                                'column':self.data_file_column_combo.get() }
            else:
                self.bell()
                return
        else:
            if self.data_synth_presets_combo.get():
                signal_spec = { 'kind':'synth',
                                'preset': self.data_synth_presets_combo.get() }
                try:
                    signal_spec['scale'] = float(self.data_scale.get())
                except ValueError:
                    signal_spec['scale'] = 1
                try:
                    signal_spec['offset'] = float(self.data_offset.get())
                except ValueError:
                    signal_spec['offset'] = 0.0
                try:
                    signal_spec['min'] = float(self.data_min.get())
                except ValueError:
                    signal_spec['min'] = -np.inf
                try:
                    signal_spec['max'] = float(self.data_max.get())
                except ValueError:
                    signal_spec['max'] = np.inf
                
                try:
                    signal_spec['stretch'] = float(self.data_stretch.get())
                except ValueError:
                    signal_spec['stretch'] = 1
                
                # prefer to restore defaults each time than leave
                # user to do it by hand
                # -- this is a bit dubious, but it's a temp hack
                self.reset_preset_adjustments()
            else:
                self.bell()
                return
        
        self.signals[namestr] = signal_spec
        self.show_signals()

    def action_remove_signal(self):
        self.sync_to_config()

        # get the ID
        namestr = self.data_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.data_field_combo.set(namestr)

        # remove it *even if invalid* (in case we somehow got a duff one in there)
        self.signals.pop(namestr, None)
        self.show_signals()
        
    def action_clear_all_signals(self):
        self.sync_to_config()
        self.signals = {}
        self.show_signals()
    
    def action_define_filter(self):
        # TODO (eventually...)
        pass

    def action_edit_presets(self):
        # TODO (eventually...)
        pass
        
    def add_output_section(self):
        self.output_section = ttk.Frame(self.sections)
        
        self.output_header_check = ttk.Checkbutton(self.output_section, text='Include Table Header', variable=self.output_header_state)
        self.output_radio_default = ttk.Radiobutton(self.output_section, text='Model Default Outputs', variable=self.output_radio_state, value=Config.OUTPUT_DEFAULT, command=self.show_output_fields)
        self.output_radio_roots = ttk.Radiobutton(self.output_section, text='Solver Variables', variable=self.output_radio_state, value=Config.OUTPUT_ROOTS, command=self.show_output_fields)
        self.output_radio_everything = ttk.Radiobutton(self.output_section, text='Everything', variable=self.output_radio_state, value=Config.OUTPUT_ALL, command=self.show_output_fields)
        self.output_radio_specify = ttk.Radiobutton(self.output_section, text='Specified Below', variable=self.output_radio_state, value=Config.OUTPUT_SPECIFY, command=self.show_output_fields)
        self.output_radio_defaults_plus = ttk.Radiobutton(self.output_section, text='Defaults + Specified', variable=self.output_radio_state, value=Config.OUTPUT_DEFAULTS_PLUS, command=self.show_output_fields)
        self.output_omit_check = ttk.Checkbutton(self.output_section, text='Model Only', variable=self.output_omit_state, command=self.show_output_fields)
        self.output_textarea = stxt.ScrolledText(self.output_section, autogrid=False)
        self.output_field_combo = ttk.Combobox(self.output_section, values=[])
        self.output_field_combo.bind('<Return>', self.action_add_output)
        self.output_field_combo.bind('<<ComboboxSelected>>', self.output_combo_validate)
        
        self.output_section.columnconfigure(1, weight=1)
        self.output_section.rowconfigure(8, weight=1)
        
        self.output_header_check.grid(row=1, column=1, sticky=tk.W)
        self.output_radio_default.grid(row=2, column=1, sticky=tk.W)
        self.output_radio_roots.grid(row=3, column=1, sticky=tk.W)
        self.output_radio_everything.grid(row=4, column=1, sticky=tk.W)
        self.output_radio_specify.grid(row=5, column=1, sticky=tk.W)
        self.output_radio_defaults_plus.grid(row=6, column=1, sticky=tk.W)
        self.output_omit_check.grid(row=6, column=2, columnspan=3, sticky=tk.W)
 
        self.output_field_combo.grid(row=7, column=1, sticky=(tk.E, tk.W))
        ttk.Button(self.output_section, text='+', width=1, command=self.action_add_output).grid(row=7, column=2, sticky=tk.W)
        ttk.Button(self.output_section, text='-', width=1, command=self.action_remove_output).grid(row=7, column=3, sticky=tk.W)
        ttk.Button(self.output_section, text='Clear', width=4, command=self.action_clear_all_outputs).grid(row=7, column=4, sticky=tk.W)
        self.output_textarea.grid(row=8, column=1, columnspan=4, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.sections.add(self.output_section, text="Outputs")    
    
    def output_combo_validate(self, args):
        if self.output_field_combo.get().startswith('-'):
            self.output_field_combo.set('')
        return None

    def action_add_output(self, *args):
        self.sync_to_config()

        # require the ID to be valid
        namestr = self.output_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.output_field_combo.set(namestr)
        else:
            self.bell()
            self.output_field_combo.set('')
            return

        if namestr not in self.explicit_outputs:
            self.explicit_outputs.append(namestr)
        self.show_output_fields()

    def action_remove_output(self):
        self.sync_to_config()
        namestr = self.output_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.output_field_combo.set(namestr)
        if namestr in self.explicit_outputs:
            self.explicit_outputs.remove(namestr)
        self.show_output_fields()        
    
    def action_clear_all_outputs(self):
        self.explicit_outputs = []
        self.sync_to_config()
        if self.config.output_subset == Config.OUTPUT_SPECIFY:
            self.output_textarea.setText('')
        
    def add_info_panel(self):
        self.info_panel = ttk.Frame(self.top_level)
        self.info_panel.columnconfigure(1, weight=1)
        self.info_panel.rowconfigure(9, weight=1)
        
        ttk.Label(self.info_panel, text='Model').grid(column=1, row=1, sticky=tk.W)
        self.model_info_field = ttk.Entry(self.info_panel, width=10, textvariable=self.model_name)
        self.model_info_field.grid(column=1, row=2, sticky=(tk.E,tk.W))

        ttk.Button(self.info_panel, image=self.load_icon, command=self.action_choose_model).grid(column=2, row=2, sticky=tk.W)        
        ttk.Button(self.info_panel, text='Parse', command=self.action_parse_info).grid(column=3, row=2, sticky=tk.W)
        ttk.Button(self.info_panel, text='Definition', command=self.action_open_def).grid(column=4, row=2, sticky=tk.W)
        
        self.graph_panel = ttk.Frame(self.info_panel)
        
        self.graph_init_check = ttk.Checkbutton(self.graph_panel, text='Initialisation', variable=self.graph_init_state)
        self.graph_unused_check = ttk.Checkbutton(self.graph_panel, text='Unused', variable=self.graph_unused_state)
        self.graph_self_check = ttk.Checkbutton(self.graph_panel, text='Params', variable=self.graph_params_state)
        self.graph_cluster_check = ttk.Checkbutton(self.graph_panel, text='Clusters', variable=self.graph_cluster_state)
        self.graph_LR_check = ttk.Checkbutton(self.graph_panel, text='Horizontal', variable=self.graph_LR_state)
        
        self.graph_init_check.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.graph_unused_check.grid(row=1, column=2, sticky=(tk.W, tk.E))
        self.graph_self_check.grid(row=1, column=3, sticky=(tk.W, tk.E))
        self.graph_cluster_check.grid(row=1, column=4, sticky=(tk.W, tk.E))
        self.graph_LR_check.grid(row=1, column=5, sticky=(tk.W, tk.E))
        
        ttk.Button(self.info_panel, text='Make', command=self.action_make_graph).grid(column=3, row=4, sticky=(tk.W, tk.E))
        ttk.Button(self.info_panel, text='View', command=self.action_view_graph).grid(column=4, row=4, sticky=(tk.W, tk.E))
        
        ttk.Label(self.info_panel, text='Dependency Graph').grid(column=1, row=3, sticky=tk.W)
        self.graph_panel.grid(row=4, column=1, columnspan=2, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.doc_panel = ttk.Frame(self.info_panel)
         
        self.doc_tabular_check = ttk.Checkbutton(self.doc_panel, text='Tabular', variable=self.doc_tabular_state)
        self.doc_display_check = ttk.Checkbutton(self.doc_panel, text='Display Style', variable=self.doc_display_state)
        self.doc_align_check = ttk.Checkbutton(self.doc_panel, text='Align Eqs', variable=self.doc_align_state)
        
        self.doc_tabular_check.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.doc_display_check.grid(row=1, column=2, sticky=(tk.W, tk.E))
        self.doc_align_check.grid(row=1, column=3, sticky=(tk.W, tk.E))
        
        ttk.Button(self.info_panel, text='HTML', command=self.action_make_html).grid(column=3, row=6, sticky=(tk.W, tk.E))
        ttk.Button(self.info_panel, text='LaTeX', command=self.action_make_latex).grid(column=4, row=6, sticky=(tk.W, tk.E))

        ttk.Label(self.info_panel, text='Documentation').grid(column=1, row=5, sticky=tk.W)
        self.doc_panel.grid(row=6, column=1, columnspan=2, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.export_panel = ttk.Frame(self.info_panel)
        self.export_derived_check = ttk.Checkbutton(self.export_panel, text='# Chem Diffs', variable=self.export_derived_state)
        self.export_derived_check.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        ttk.Button(self.info_panel, text='ModelDef', command=self.action_make_modeldef).grid(column=3, row=8, sticky=(tk.W, tk.E))
        if doc_sbml.AVAILABLE:
            ttk.Button(self.info_panel, text='SBML', command=self.action_make_sbml).grid(column=4, row=8, sticky=(tk.W, tk.E))
        else:
            ttk.Button(self.info_panel, text='SBML', state='disabled', command=self.action_make_sbml).grid(column=4, row=8, sticky=(tk.W, tk.E))
        
        ttk.Label(self.info_panel, text='Model Export').grid(column=1, row=7, sticky=tk.W)
        self.export_panel.grid(row=8, column=1, columnspan=2, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.info_text = stxt.ScrolledText(self.info_panel, autogrid=False)
        self.info_text.grid(row=9, column=1, columnspan=4, sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.top_level.add(self.info_panel, text='Info')

    def add_optim_panel(self):
        self.optim_panel = ttk.Frame(self.top_level)
        self.optim_panel.columnconfigure(1, weight=1)
        self.optim_panel.rowconfigure(1, weight=1)
        self.top_level.add(self.optim_panel, text='Optimisation')
        
    def add_abc_panel(self):
        self.abc_panel = ttk.Frame(self.top_level)
        self.abc_panel.columnconfigure(1, weight=1)
        self.abc_panel.rowconfigure(1, weight=1)
        self.top_level.add(self.abc_panel, text='ABC ')
    
    # mediate between configuration and onscreen controls
    def sync_to_config(self):
        self.config.debug = bool(self.debug_state.get())
        self.config.match_input = bool(self.match_state.get())
        self.config.coarse = bool(self.coarse_state.get())
        self.config.detail = bool(self.detail_state.get())
        self.config.model_name = self.model_name.get()
        self.config.input_file = self.input_name.get()
        self.config.coarse_name = self.coarse_name.get()
        self.config.detail_name = self.detail_name.get()
        self.config.generate_name = self.generate_name.get()
        self.config.use_generated = bool(self.use_generated_state.get())
        self.config.graph_unused = bool(self.graph_unused_state.get())
        self.config.graph_init = bool(self.graph_init_state.get())
        self.config.graph_params = bool(self.graph_params_state.get())
        self.config.graph_clusters = bool(self.graph_cluster_state.get())
        self.config.graph_LR = bool(self.graph_LR_state.get())
        
        self.config.param_file = self.param_file_name.get()
        self.config.use_param_file = bool(self.param_file_state.get())
        self.config.omit_non_model_params = bool(self.param_omit_state.get())
        self.config.use_explicit = bool(self.param_explicit_state.get())
        self.config.do_steady = bool(self.param_steady_state.get())
        try:
            self.config.steady_duration = float(decimal.Decimal(self.param_steady_duration.get()))
        except decimal.InvalidOperation:
            # leave last setting unchanged -- it'll sync back soon enough
            pass
        
        self.config.time_from_file = self.time_radio_state.get()
        self.config.time_file = self.time_file_name.get()
        self.config.priority = self.time_priority_state.get()
        try:
            self.config.time_rate = float(decimal.Decimal(self.time_rate.get()))
        except decimal.InvalidOperation:
            pass
        try:
            self.config.time_duration = float(decimal.Decimal(self.time_duration.get()))
        except decimal.InvalidOperation:
            pass
        self.config.data_file = self.data_file_name.get()
        self.config.shared_data_file = bool(self.data_file_same_state.get())
        self.config.data_source = self.data_source_state.get()
        
        self.config.output_header = bool(self.output_header_state.get())
        self.config.output_model_only = bool(self.output_omit_state.get())
        self.config.output_subset = self.output_radio_state.get()

        self.config.latex_tabular = bool(self.doc_tabular_state.get())
        self.config.latex_displaystyle = bool(self.doc_display_state.get())
        self.config.latex_align = bool(self.doc_align_state.get())
        
        self.config.export_derived = bool(self.export_derived_state.get())


    def sync_from_config(self):
        self.debug_state.set(int(self.config.debug))
        self.match_state.set(int(self.config.match_input))
        self.coarse_state.set(int(self.config.coarse))
        self.detail_state.set(int(self.config.detail))
        self.model_name.set(self.config.model_name)
        self.input_name.set(self.config.input_file)
        self.coarse_name.set(self.config.coarse_name)
        self.detail_name.set(self.config.detail_name)
        self.generate_name.set(self.config.generate_name)
        self.use_generated_state.set(int(self.config.use_generated))
        self.graph_unused_state.set(int(self.config.graph_unused))
        self.graph_init_state.set(int(self.config.graph_init))
        self.graph_params_state.set(int(self.config.graph_params))
        self.graph_cluster_state.set(int(self.config.graph_clusters))
        self.graph_LR_state.set(int(self.config.graph_LR))
        
        self.param_file_name.set(self.config.param_file)
        self.param_file_state.set(int(self.config.use_param_file))
        self.param_omit_state.set(int(self.config.omit_non_model_params))
        self.param_explicit_state.set(int(self.config.use_explicit))
        self.param_steady_state.set(int(self.config.do_steady))
        self.param_steady_duration.set(str(self.config.steady_duration))
        
        self.time_radio_state.set(self.config.time_from_file)
        self.time_file_name.set(self.config.time_file)
        self.time_priority_state.set(self.config.priority)
        self.time_rate.set(str(self.config.time_rate))
        self.time_duration.set(str(self.config.time_duration))
        self.data_file_name.set(self.config.data_file)
        self.data_file_same_state.set(int(self.config.shared_data_file))
        self.data_source_state.set(self.config.data_source)
        
        self.output_header_state.set(int(self.config.output_header))
        self.output_omit_state.set(int(self.config.output_model_only))
        self.output_radio_state.set(int(self.config.output_subset))
        
        self.doc_tabular_state.set(int(self.config.latex_tabular))
        self.doc_display_state.set(int(self.config.latex_displaystyle))
        self.doc_align_state.set(int(self.config.latex_align))

        self.export_derived_state.set(int(self.config.export_derived))

    # Event handlers
    
    # build the current model from its source
    def action_build(self, *args):
        self.sync_to_config()
        self.app_log.log('generating C code for %s' % self.model_name.get())
        self.winfo_toplevel().update_idletasks()
        result, logfile = Executor.parse(self.config)
        
        self.build_log.fromFile(logfile)
        
        if result:
            self.app_log.log('compilation failed with exit code %d (see build log for details)' % result)
        else:   
            if self.config.auto_parse:
                self.app_log.log('reading model info %s%s' % (self.model_name.get(), self.config.extensions['parsed']))
                self.action_parse_info()
            self.app_log.log('compiling %s%s' % (self.model_name.get(), self.config.extensions['model']))
            self.winfo_toplevel().update_idletasks()
            result, out, err = Executor.compile(self.config)
            self.stdout_log.setText(out)
            self.stderr_log.setText(err)
            if result:
                self.app_log.log('compilation failed with exit code %d (check stdout/stderr for more info)' % result)
            else:
                self.app_log.log('build complete')

    # run the current model
    def action_run(self):
        self.sync_to_config()
        
        # running with no output at all is pointless, so check for that
        if not (self.config.coarse or self.config.detail):
            self.app_log.log('no outputs requested, model not run')
            return
        
        self.app_log.log('running %s%s with %s' % (self.config.model_name, self.config.extensions['model'], self.config.input_file))
        self.winfo_toplevel().update_idletasks()
        result, out, err = Executor.run(self.config)
        self.stdout_log.fromFile(out)
        self.stderr_log.fromFile(err)
        if result:
            self.app_log.log('model returned exit code %d (see stdout/stderr for more info)' % result)
        else:
            self.app_log.log('model run completed')
    
    # parse the model info file and stick the results in the info panel
    def action_parse_info(self):
        self.sync_to_config()
        
        info.CONFIG['name'] = self.config.model_name
        info.CONFIG['filename'] = os.path.join(self.config.work, self.config.model_name + self.config.extensions['parsed'])
        
        self.parsed_model = info.load_model(info.CONFIG)
        self.info_text.setText(info.modelInfo(self.parsed_model, info.CONFIG))
        self.show_initial_values()
        self.show_output_fields()
        
        # set appropriate values in the popups
        model_vars = ['-- Model Variables --'] + sorted(self.parsed_model['roots'], key=str.lower)
        intermeds = sorted(self.parsed_model['intermeds'], key=str.lower)
        if intermeds: intermeds = ['-- Intermediates --'] + intermeds
        params = sorted(self.parsed_model['params'], key=str.lower)
        if params: params = ['-- Parameters --'] + params
        inputs = sorted(self.parsed_model['inputs'], key=str.lower)
        if inputs: inputs = ['-- Inputs --'] + inputs
        
        init_names = model_vars + intermeds + params
        input_names = inputs + model_vars + intermeds + params
        
        self.param_field_combo['values'] = init_names
        self.output_field_combo['values'] = input_names
        self.data_field_combo['values'] = input_names
    
    # open model definition in a text window
    def action_open_def(self):
        self.sync_to_config()
        file = os.path.join(self.config.model_dir, self.config.model_src)
        
        # TODO: make this more robust
        if file in self.floaters:
            self.floaters[file]['text'].fromFile(file)
            self.floaters[file]['window'].lift()
        else:
            win = tk.Toplevel(self)
            win.title(self.config.model_src)
            txt = stxt.ScrolledText(win, autogrid=True, wrap='none')
            txt.fromFile(file)
            # temporarily removed until can be made robust
            # self.floaters[file] = { 'text':txt, 'window':win }
            win.lift()
    
    # generate a graph of the model
    def action_make_graph(self):
        self.sync_to_config()
        
        # a rare concession to consistency -- parse info if we haven't already
        # we make no other attempt to ensure we're up to date...
        if self.parsed_model is None:
            self.action_parse_info()
        
        info.CONFIG['graph-exclude-unused'] = not self.config.graph_unused
        info.CONFIG['graph-exclude-init'] = not self.config.graph_init
        info.CONFIG['graph-exclude-clusters'] = not self.config.graph_clusters
        info.CONFIG['graph-exclude-self'] = not self.config.graph_self
        info.CONFIG['graph-exclude-params'] = not self.config.graph_params
        info.CONFIG['graph-horizontal'] = self.config.graph_LR
        
        gv = info.generateGraphViz(self.parsed_model, info.CONFIG)
        
        with open(os.path.join(self.config.work, self.config.model_name + self.config.extensions['graphviz']), 'w') as f:
            print >> f, gv
        
        self.gif_name = Executor.graph(self.config)
        if not self.gif_name:
            # TODO: some kind of alert?
            pass
    
    # view the GIF version of the generated graph
    def action_view_graph(self):
        if self.gif_name:
            win = tk.Toplevel(self)
            win.title(self.gif_name)
            img = simg.ScrolledImage(win, autogrid=True)
            img.canvas.config(width=self.config.default_width, height=self.config.default_height)
            img.fromFile(self.gif_name)
            win.lift()

    def action_make_html(self):
        self.sync_to_config()
        
        if self.parsed_model is None:
            self.action_parse_info()
        
        info.CONFIG['outdir'] = self.config.work
        info.CONFIG['name'] = self.config.model_name
        info.CONFIG['html'] = self.config.model_name + self.config.extensions['html']

        doc_html.writeDoc(self.parsed_model, info.CONFIG)
    
    
    def action_make_latex(self):
        self.sync_to_config()
        
        if self.parsed_model is None:
            self.action_parse_info()
        
        info.CONFIG['outdir'] = self.config.work
        info.CONFIG['name'] = self.config.model_name
        info.CONFIG['latex'] = self.config.model_name + self.config.extensions['latex']
        
        info.CONFIG['eq-align'] = self.config.latex_align
        info.CONFIG['latex-display-style'] = self.config.latex_displaystyle
        info.CONFIG['latex-tabular'] = self.config.latex_tabular

        doc_latex.writeDoc(self.parsed_model, info.CONFIG)
    
    def action_make_modeldef(self):
        self.sync_to_config()
        
        if self.parsed_model is None:
            self.action_parse_info()
        
        info.CONFIG['outdir'] = self.config.work
        info.CONFIG['name'] = self.config.model_name
        info.CONFIG['model-comment-chem-diffs'] = self.config.export_derived
        info.CONFIG['modeldef'] = self.config.model_name + self.config.extensions['modeldef']

        doc_modeldef.writeDoc(self.parsed_model, info.CONFIG)
        
    def action_make_sbml(self):
        self.sync_to_config()
        
        if self.parsed_model is None:
            self.action_parse_info()
        
        info.CONFIG['outdir'] = self.config.work
        info.CONFIG['name'] = self.config.model_name
        info.CONFIG['sbml'] = self.config.model_name + self.config.extensions['sbml']

        doc_sbml.writeDoc(self.parsed_model, info.CONFIG)
        
    
    # choose a model definition
    def action_choose_model(self):
        self.sync_to_config()
        options = { 'defaultextension': self.config.extensions['modeldef'],
                    'filetypes': [('BCMD Model Definition', self.config.extensions['modeldef']), ('All Files', '.*')],
                    'initialdir': self.config.model_dir,
                    'parent': self,
                    'title': 'Choose Model Definition' }
        self.config.set_model(tkFileDialog.askopenfilename(**options))
        self.sync_from_config()
        
    # choose an input file
    def action_choose_input(self):
        self.sync_to_config()
        options = { 'defaultextension': self.config.extensions['input'],
                    'filetypes': [('BCMD Input File', self.config.extensions['input']),
                                  ('All Files', '.*')],
                    'initialdir': self.config.input_dir,
                    'parent': self,
                    'title': 'Choose Input File' }
        self.config.set_input(tkFileDialog.askopenfilename(**options))
        self.sync_from_config()
    
    # choose a parameter init file
    def action_choose_param_file(self):
        self.sync_to_config()
        options = { 'defaultextension': self.config.extensions['input'],
                    'filetypes': [('BRAINCIRC Input File', self.config.extensions['braincirc']),
                                  ('Comma Separated Value File', self.config.extensions['csv']),
                                  ('Tab-delimited Text File', self.config.extensions['txt']),
                                  ('All Files', '.*')],
                    'initialdir': os.path.split(self.config.param_file)[0],
                    'parent': self,
                    'title': 'Choose Parameter File' }
        self.config.set_param_file(tkFileDialog.askopenfilename(**options))
        self.sync_from_config()
        self.load_param_vals()
    
    # load parameter values from file
    def load_param_vals(self):
        try:
            contents = inputs.readValues(self.config.param_file)
            #print contents
            if isinstance(contents, dict):
                self.file_params = contents
            self.show_initial_values()
        except:
            pass

    # choose a time source
    def action_choose_time_file(self):
        self.sync_to_config()
        initdir = os.path.split(self.config.time_file)[0]
        if not initdir: initdir = self.config.input_dir
        options = { 'defaultextension': self.config.extensions['txt'],
                    'filetypes': [('Tab-delimited Text File', self.config.extensions['txt']),
                                ('CSV File', self.config.extensions['csv']),
                                ('All Files', '.*')],
                    'initialdir': initdir,
                    'parent': self,
                    'title': 'Choose Time File' }
        self.config.set_time_file(tkFileDialog.askopenfilename(**options))
        self.sync_from_config()
        self.load_time_file()
        self.show_signals()
    
    def load_time_file(self):
        try:
            self.time_contents = inputs.readCSV(self.config.time_file, wrap_timeseries=False)
            self.time_file_combo['values'] = self.time_contents.keys()
            if self.config.shared_data_file:
                self.data_contents = self.time_contents
                self.data_file_column_combo['values'] = self.time_contents.keys()
        except:
            # TODO: log an error somewhere
            pass
 
    def load_data_file(self):
        try:
            self.data_contents = inputs.readCSV(self.config.data_file, wrap_timeseries=False)
            self.data_file_column_combo['values'] = self.data_contents.keys()
            if self.config.shared_data_file:
                self.time_contents = self.data_contents
                self.time_file_combo['values'] = self.time_contents.keys()
        except:
            # TODO: log an error somewhere
            pass

    # choose a data source
    def action_choose_data_file(self):
        self.sync_to_config()
        initdir = os.path.split(self.config.data_file)[0]
        if not initdir: initdir = self.config.input_dir
        options = { 'defaultextension': self.config.extensions['txt'],
                    'filetypes': [('Tab-delimited Text File', self.config.extensions['txt']),
                                  ('CSV File', self.config.extensions['csv']),
                                  ('All Files', '.*')],
                    'initialdir': initdir,
                    'parent': self,
                    'title': 'Choose Data File' }
        self.config.set_data_file(tkFileDialog.askopenfilename(**options))
        self.sync_from_config()
        self.load_data_file()
        self.show_signals()
 
    # choose the directory to generate input files in
    def action_choose_generate_dir(self):
        self.sync_to_config()
        options = { 'initialdir': self.config.generate_dir,
                    'parent': self,
                    'title': 'Choose Directory' }
        self.config.set_generate_dir(tkFileDialog.askdirectory(**options))
        self.sync_from_config()

    def action_add_explicit(self):
        self.sync_to_config()

        # require the ID to be valid
        namestr = self.param_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.param_field_combo.set(namestr)
        else:
            self.bell()
            self.param_field_combo.set('')
            return
            
        # ditto the value to be assigned
        valstr = self.param_value_field.get().strip()
        try:
            value = decimal.Decimal(valstr)
        except decimal.InvalidOperation:
            self.bell()
            self.param_value.set('')
            return
        self.param_value.set(valstr)
        
        # record both and update the display
        self.explicit_params[namestr] = valstr
        self.show_initial_values()
        
    def action_remove_explicit(self):
        self.sync_to_config()

        # get the ID
        namestr = self.param_field_combo.get().strip()
        if Validator.is_valid_id(namestr):
            self.param_field_combo.set(namestr)

        # remove it *even if invalid* (in case we somehow got a duff one in there)
        self.explicit_params.pop(namestr, None)
        self.show_initial_values()
         
    def action_clear_all_explicits(self):
        self.sync_to_config()
        self.explicit_params = {}
        self.show_initial_values()
    
    # generate an input file
    def action_generate(self, *args):
        self.sync_to_config()
        filepath = os.path.join(self.config.generate_dir, self.config.generate_name)
        lines, step_count = self.calculate_steps()
        with open(filepath, 'w') as f:
            print >> f, '# BCMD input file generated by BGUI'
            print >> f, '@ %d' % step_count
            for line in lines:
                print >> f, line
        if self.config.use_generated:
            self.config.set_input(filepath)
            self.sync_from_config()
    
    # construct the steps for an input file, as a simple list of strings
    def calculate_steps(self):
        lines = []
        step_count = 0
        
        init_names = []
        init_vals = []
        
        if self.config.use_explicit:
            for name in sorted(self.explicit_params.keys(), key=str.lower):
                if self.parsed_model is None or name in self.parsed_model['symlist'] or not self.config.omit_non_model_params:
                    init_names.append(name)
                    init_vals.append(self.explicit_params[name])
        
        if self.config.use_param_file:
            for name in sorted(self.file_params.keys(), key=str.lower):
                if name not in init_names and (self.parsed_model is None or name in self.parsed_model['symlist'] or not self.config.omit_non_model_params):
                    init_names.append(name)
                    init_vals.append(self.file_params[name])

        if init_names or (self.config.do_steady and self.config.steady_duration):
            lines.append('# suppress output during preamble')
            lines.append('>>> 0')
            lines.append('!0')
        
        # split long initialisations across multiple lines
        n_init_lines = int(np.ceil(len(init_names)/float(self.config.max_inits)))
        
        if n_init_lines > 0:
            lines.append('# initial values')
        
        for ii in range(n_init_lines):
            names = init_names[(ii*self.config.max_inits):((ii+1)*self.config.max_inits)]
            vals = [str(x) for x in init_vals[(ii*self.config.max_inits):((ii+1)*self.config.max_inits)]]
            lines.append(': %d %s' % (len(names), ' '.join(names)))
            lines.append('= 0 0 %s' % ' '.join(vals))
            step_count += 1
        
        if self.config.do_steady and self.config.steady_duration:
            # TODO: adjust to align times if first time point in real sequence is not 0
            lines.append('# run for a bit to equilibrate')
            lines.append(': 0')
            lines.append('= %g 0' % -self.config.steady_duration)
            step_count += 1
        
        # preamble over, specify real outputs
        lines.append('# specify outputs')
        if self.config.output_header:
            lines.append('!!!')
        
        out_list = None
        if self.config.output_subset == Config.OUTPUT_ROOTS:
            if self.parsed_model is not None:
                out_list = self.parsed_model.get('roots', [])
                if self.parsed_model['symlist'][0] not in out_list:
                    out_list.append(self.parsed_model['symlist'][0])
        elif self.config.output_subset == Config.OUTPUT_ALL:
            if self.parsed_model is not None:
                out_list = self.parsed_model.get('symlist', [])
        elif self.config.output_subset == Config.OUTPUT_SPECIFY or self.config.output_subset == Config.OUTPUT_DEFAULTS_PLUS:
            out_list = [ x for x in self.explicit_outputs
                         if (self.parsed_model is None or x in self.parsed_model['symlist'] or not self.config.output_model_only) ]
            if self.config.output_subset == Config.OUTPUT_DEFAULTS_PLUS:
                outputs = self.parsed_model.get('outputs', [])
                if not outputs: outputs = self.parsed_model.get('roots',[])
                out_list += [x for x in outputs if x not in out_list]
                if self.parsed_model['symlist'][0] not in out_list:
                    out_list.append(self.parsed_model['symlist'][0])
        
        if out_list:
            lines.append('>>> %d %s' % (len(out_list), ' '.join(out_list)))
        else:
            lines.append('>>> *')
        
        # now to insert some actual steps
        
        time, data = self.marshal_signals()
        names = sorted(data.keys(), key=str.lower)
        
        # for the moment we only implement policies that do not
        # require changing settings as we go
        # and we should also be guaranteed non-empty lists
        
        lines.append('# now the actual simulation steps')
        lines.append((': %d ' % len(names)) + ' '.join(names))
        
        for ii in range(len(time['start'])):
            vals = [ str(data[name][ii]) for name in names]
            lines.append('= %g %g %s' % (time['start'][ii], time['end'][ii], ' '.join(vals)))
            step_count += 1
        
        return lines, step_count
        
    
    def show_initial_values(self):
        self.sync_to_config()
        if self.config.use_param_file and not self.file_params:
            self.load_param_vals()
        if self.config.use_explicit:
            explicit_lines = [ '%s = %s' % (x, self.explicit_params[x])
                                for x in sorted(self.explicit_params.keys(), key=str.lower)
                                if ( self.parsed_model is None or x in self.parsed_model['symlist'] or not self.config.omit_non_model_params ) ]
            ivstr = '-- Explicit Parameters --\n' + '\n'.join(explicit_lines)
            
            if self.config.use_param_file:
                file_lines = [ '%s = %s' % (x, self.file_params[x])
                               for x in sorted(self.file_params.keys(), key=str.lower)
                               if x not in self.explicit_params and ( self.parsed_model is None or x in self.parsed_model['symlist'] or not self.config.omit_non_model_params ) ]
                ivstr += '\n-- File Parameters --\n' + '\n'.join(file_lines)
        
        elif self.config.use_param_file:
            file_lines = [ '%s = %s' % (x, self.file_params[x])
                            for x in sorted(self.file_params.keys(), key=str.lower)
                            if (self.parsed_model is None or x in self.parsed_model['symlist'] or not self.config.omit_non_model_params ) ]
            ivstr = '-- File Parameters --\n' + '\n'.join(file_lines)
        else:
            ivstr = '-- no initial values --'
        
        self.param_textarea.setText(ivstr)
 
    def show_output_fields(self):
        self.sync_to_config()
        field_list = []
        if self.config.output_subset == Config.OUTPUT_DEFAULT:
            if self.parsed_model is not None:
                if 'outputs' in self.parsed_model:
                    field_list = self.parsed_model['outputs']
                else:
                    field_list = self.parsed_model.get('roots', [])
                if self.parsed_model['symlist'][0] not in field_list:
                    field_list.append(self.parsed_model['symlist'][0])
        elif self.config.output_subset == Config.OUTPUT_ROOTS:
            if self.parsed_model is not None:
                field_list = self.parsed_model.get('roots', [])
                if self.parsed_model['symlist'][0] not in field_list:
                    field_list.append(self.parsed_model['symlist'][0])
        elif self.config.output_subset == Config.OUTPUT_ALL:
            if self.parsed_model is not None:
                field_list = self.parsed_model.get('symlist', [])
        else:    
            field_list = [ x for x in self.explicit_outputs
                           if (self.parsed_model is None or x in self.parsed_model['symlist'] or not self.config.output_model_only) ]
            if self.config.output_subset == Config.OUTPUT_DEFAULTS_PLUS and self.parsed_model is not None:
                outputs = self.parsed_model.get('outputs', [])
                if not outputs: outputs = self.parsed_model.get('roots',[])
                field_list += [x for x in outputs if x not in field_list]
                if self.parsed_model['symlist'][0] not in field_list:
                    field_list.append(self.parsed_model['symlist'][0])
        
        self.output_textarea.setText('\n'.join(sorted(field_list, key=str.lower)))
    
    
    # open the coarse results in a text window
    def action_open_coarse(self):
        file = os.path.join(self.config.work, self.config.coarse_name)
        
        # TODO: make this more robust
        if file in self.floaters:
            self.floaters[file]['text'].fromFile(file)
            self.floaters[file]['window'].lift()
        else:
            win = tk.Toplevel(self)
            win.title(self.config.coarse_name)
            txt = stxt.ScrolledText(win, autogrid=True, wrap='none')
            txt.fromFile(file)
            # temporarily removed until can be made robust
            # self.floaters[file] = { 'text':txt, 'window':win }
            win.lift()
    
    # likewise for the detailed results
    def action_open_detail(self):
        file = os.path.join(self.config.work, self.config.detail_name)
        
        # TODO: make this more robust
        if file in self.floaters:
            self.floaters[file]['text'].fromFile(file)
            self.floaters[file]['window'].lift()
        else:
            win = tk.Toplevel(self)
            win.title(self.config.detail_name)
            txt = stxt.ScrolledText(win, autogrid=True, wrap='none')
            txt.fromFile(file)
            # temporarily removed until can be made robust
            # self.floaters[file] = { 'text':txt, 'window':win }
            win.lift()

    def action_plot_coarse(self):
        file = os.path.join(self.config.work, self.config.coarse_name)
        dict = inputs.readCSV(file, wrap_timeseries=False)
        
        chooser = chx.AxisChooser(self, fields=dict.keys() + [''], title='Configure Plot')
        
        if chooser.result and (chooser.result['x'] or chooser.result['y']):        
            win = tk.Toplevel(self)
            win.title('Coarse Results: %s' % self.config.model_name)
        
            if chooser.result['x']:
                plotter = splt.SimplePlot(win, figsize=(10,6))
                if chooser.result['y']:
                    plotter.subplot.plot(dict[chooser.result['x']], dict[chooser.result['y']], chooser.result['type'])
                    plotter.subplot.set_xlabel(chooser.result['x'])
                    plotter.subplot.set_ylabel(chooser.result['y'])
                else:
                    plotter.subplot.plot(dict[chooser.result['x']], range(len(dict[chooser.result['x']])), chooser.result['type'])
                    plotter.subplot.set_xlabel(chooser.result['x'])
                    plotter.subplot.set_ylabel('Index')
            else:
                plotter = splt.SimplePlot(win, figsize=(10,6))
                plotter.subplot.plot(dict[chooser.result['y']], chooser.result['type'])
                plotter.subplot.set_xlabel('Index')
                plotter.subplot.set_ylabel(chooser.result['y'])
        
            win.lift()
    
    def action_plot_detail(self):
        file = os.path.join(self.config.work, self.config.detail_name)
        dict = inputs.readCSV(file, wrap_timeseries=False)
        
        chooser = chx.AxisChooser(self, fields=dict.keys() + [''], title='Configure Plot')
        
        if chooser.result and (chooser.result['x'] or chooser.result['y']):
            win = tk.Toplevel(self)
            win.title('Detailed Results: %s' % self.config.model_name)
        
            if chooser.result['x']:
                plotter = splt.SimplePlot(win, figsize=(10,6))
                if chooser.result['y']:
                    plotter.subplot.plot(dict[chooser.result['x']], dict[chooser.result['y']], chooser.result['type'])
                    plotter.subplot.set_xlabel(chooser.result['x'])
                    plotter.subplot.set_ylabel(chooser.result['y'])
                else:
                    plotter.subplot.plot(dict[chooser.result['x']], range(len(dict[chooser.result['x']])), chooser.result['type'])
                    plotter.subplot.set_xlabel(chooser.result['x'])
                    plotter.subplot.set_ylabel('Index')
            else:
                plotter = splt.SimplePlot(win, figsize=(10,6))
                plotter.subplot.plot(dict[chooser.result['y']], chooser.result['type'])
                plotter.subplot.set_xlabel('Index')
                plotter.subplot.set_ylabel(chooser.result['y'])
        
            win.lift()
