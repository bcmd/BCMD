# module handling configuration and preferences for the BCMD GUI

import sys, os, os.path
import pprint, argparse

# environment and default settings
VERSION = 0.5
BCMD_HOME = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
USER_HOME = os.path.expanduser('~')
PARSER = os.path.join(BCMD_HOME, 'bparser')
ABC = os.path.join(BCMD_HOME, 'abc')
PREFS = os.extsep + 'bcmd_prefs'
WORK = os.path.join(BCMD_HOME, 'build')
RESOURCES = os.path.join(BCMD_HOME, 'resources')
MODEL_PATH = [ os.path.join(BCMD_HOME, 'examples') ]
INPUT_PATH = [ os.path.join(BCMD_HOME, 'examples') ]

PREF_FIELDS = [ 'model_path', 'input_path',
                'model_name', 'model_src', 'model_dir',
                'input_file', 'input_dir',
                'debug', 'match_input', 'match_outputs',
                'coarse', 'detail',
                'coarse_name', 'detail_name',
                
                'generate_name', 'generate_dir',
                'use_generated', 'run_generated',
                
                'graph_unused', 'graph_init',
                'graph_self', 'graph_clusters',
                'graph_params', 'graph_LR',
                
                'latex_tabular', 'latex_displaystyle',
                'latex_align',
                
                'export_derived',
                
                'param_file', 'use_param_file',
                'use_explicit', 'omit_non_model_params',
                'steady_duration', 'do_steady',
                'match_inputs',
                
                'time_from_file', 'time_file',
                'time_rate', 'time_duration',
                'priority',
                
                'data_file', 'shared_data_file',
                'data_source',

#                'presets',
                
                'output_header', 'output_subset',
                'output_model_only',
                
                'max_inits',
                
                'auto_parse']

EXTENSIONS = {'model': os.extsep + 'model',
              'modeldef': os.extsep + 'modeldef',
              'input': os.extsep + 'input',
              'log': os.extsep + 'log',
              'out': os.extsep + 'out',
              'detail': os.extsep + 'detail',
              'stderr': os.extsep + 'stderr',
              'stdout': os.extsep + 'stdout',
              'parsed': os.extsep + 'bcmpl',
              'graphviz': os.extsep + 'gv',
              'pdf': os.extsep + 'pdf',
              'gif': os.extsep + 'gif',
              'braincirc': os.extsep + 'dat',
              'txt' : os.extsep + 'txt',
              'csv' : os.extsep + 'csv',
              'latex' : os.extsep + 'tex',
              'html' : os.extsep + 'html',
              'sbml' : os.extsep + 'xml'
              }

FACTORY_PRESETS =  { 'Noise: N(0,1)' : [{ 'kind':'gaussian', 'lo':None }],
                     'Noise: U(0,1)' : [{ 'kind':'uniform' }],
                     'Random Walk' : [{ 'kind':'walk', 'sd':0.1, 'lo':None }],
                     'Sine 1 Hz, [0,1]': [{ 'kind':'sine', 'freq':1 }],
                     'Saw 1 Hz, [0,1]': [{ 'kind':'saw', 'freq':1 }],
                     'Square 1 Hz, [0,1]': [{ 'kind':'square', 'freq':1 }],
                     
                     'NIRS mix, [0,1]': [ { 'kind':'sine', 'freq':1.00, 'lo':-0.6, 'hi':0.6 },
                                          { 'kind':'sine', 'freq':0.25, 'lo':-0.2, 'hi':0.2 },
                                          { 'kind':'sine', 'freq':0.10, 'lo':-0.9, 'hi':0.9 },
                                          { 'kind':'sine', 'freq':0.04, 'lo':-1.0, 'hi':1.0 },
                                          { 'kind':'gaussian', 'sd':0.053 },
                                          { 'kind':'rescale', 'lo':0, 'hi':1 } ]
                   }

MODEL_NAME = 'BrainSignals'

# numeric 'constants' representing choices
OUTPUT_DEFAULT = 0
OUTPUT_ROOTS = 1
OUTPUT_ALL = 2
OUTPUT_SPECIFY = 3
OUTPUT_DEFAULTS_PLUS = 4
TIME_FROM_FILE = 0
TIME_SPECIFY = 1
PRIORITISE_DATA = 0
PRIORITISE_TIME = 1
FILE_DATA = 0
SYNTH_DATA = 1

# some of these details may get overridden by prefs file, but set defaults here
class Config(object):
    def __init__(self, args=[]):
        self.home = BCMD_HOME
        self.parser = PARSER
        self.prefs = os.path.join(USER_HOME, PREFS)
        self.work = WORK
        self.resources = RESOURCES
        self.model_path = MODEL_PATH
        self.input_path = INPUT_PATH        
        self.extensions = EXTENSIONS
        
        self.model_name = MODEL_NAME
        self.model_src = MODEL_NAME + EXTENSIONS['modeldef']
        self.input_file = MODEL_NAME + EXTENSIONS['input']
        self.model_dir = MODEL_PATH[0]
        self.input_dir = INPUT_PATH[0]
        
        self.debug_verbosity = 5
        self.release_verbosity = 5
        
        self.debug = True
        self.match_input = True
        self.match_outputs = True
        self.coarse = True
        self.detail = False
        self.coarse_name = MODEL_NAME + EXTENSIONS['out']
        self.detail_name = MODEL_NAME + EXTENSIONS['detail']
        
        self.generate_name = 'generated' + EXTENSIONS['input']
        self.generate_dir = self.input_dir
        self.use_generated = True
        self.run_generated = True
        
        self.graph_unused = True
        self.graph_init = True
        self.graph_self = False
        self.graph_clusters = True
        self.graph_params = True
        self.graph_LR = False
        
        self.latex_tabular = False
        self.latex_displaystyle = True
        self.latex_align = False
        
        self.export_derived = False
        
        self.default_width = 800
        self.default_height= 600
        
        self.param_file = os.path.join(self.input_dir, 'params' + EXTENSIONS['input'])
        self.use_param_file = False
        self.use_explicit = False
        self.omit_non_model_params = True
        self.steady_duration = 1000
        self.do_steady = 0
        
        self.match_inputs = True

        self.time_from_file = TIME_FROM_FILE
        self.time_file = ''
        self.time_rate = 100
        self.time_duration = 10
        self.priority = PRIORITISE_DATA
        self.data_file = ''
        self.shared_data_file = True
        self.data_source = SYNTH_DATA

        self.output_header = True
        self.output_subset = OUTPUT_DEFAULT
        self.output_model_only = True
        
        self.auto_parse = True
        self.max_inits = 20
        
        self.presets = FACTORY_PRESETS
        
        # arg processing precedes loading so that we can specify a different config
        self.process_args(args)
        
        self.load()

    
    def process_args(self, args):
        # TODO
        pass
    
    def load(self):
        try:
            with open(self.prefs) as f:
                prefs = eval(f.read())
            for field in PREF_FIELDS:
                if field in prefs:
                    self.__dict__[field] = prefs[field]
        except IOError as e:
            print >> sys.stderr, "Error loading configuration file %s: %s" % (self.prefs, e.strerror)
    
    def save(self):
        try:
            with open(self.prefs, 'w') as f:
                pprint.pprint(self.__dict__, stream=f)
        except IOError as e:
            print >> sys.stderr, "Error saving configuration file %s: %s" % (self.prefs, e.strerror)
    
    
    def set_model(self, fullpath):
        if fullpath:
            path, file = os.path.split(fullpath)
            name, ext = os.path.splitext(file)
        
            self.model_name = name
            self.model_src = file
            self.model_dir = path
            
            if self.match_input:
                self.input_file = name + self.extensions['input']
                
                if self.match_outputs:
                    self.coarse_name = name + self.extensions['out']
                    self.detail_name = name + self.extensions['detail']
                
                # TODO: actually search the input path?
                self.input_dir = path
    
    def set_input(self, fullpath):
        if fullpath:
            self.input_dir, self.input_file = os.path.split(fullpath)
            
            if self.match_outputs:
                input_base = os.path.splitext(self.input_file)[0]
                self.coarse_name = input_base + self.extensions['out']
                self.detail_name = input_base + self.extensions['detail']
    
    def set_param_file(self, fullpath):
        if fullpath:
            self.param_file = fullpath
            self.use_param_file = True
    
    def get_model_path_list(self):
        # may want to be a bit more sophisticated about this later
        return [self.model_dir] + self.model_path
    
    def set_generate_dir(self, dir):
        if dir:
            self.generate_dir = dir

    def set_time_file(self, fullpath):
        if fullpath:
            self.time_file = fullpath
            if self.shared_data_file:
                self.data_file = fullpath

    def set_data_file(self, fullpath):
        if fullpath:
            self.data_file = fullpath
            if self.shared_data_file:
                self.time_file = fullpath
