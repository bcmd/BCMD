import sys
import pprint

# extremely minimal logging module for writing out messages at
# quasi-arbitrary verbosity levels -- some standard levels are
# defined, but module can also be used with arbitrary levels
DISASTER = -1
ERROR = 1
WARNING = 3
MESSAGE = 5
DETAIL = 7

# default verbosity hides messages and 
verbosity = WARNING
deathThrows = True

# go to stderr by default
dest = sys.stderr

# just write it
def write(msg, level=1):
    if level <= verbosity:
        print >> dest, msg

# prettify it first
def pretty(msg, level=1):
    if level <= verbosity:
        if isinstance(msg, str):
            print >> dest, msg
        else:
            print >> dest, pprint.pformat(msg)

# some message level wrappers
def error(msg, prettify=False):
    if prettify: pretty(msg, level=ERROR)
    else: write(msg, level=ERROR)

def warn(msg, prettify=False):
    if prettify: pretty(msg, level=WARNING)
    else: write(msg, level=WARNING)

def message(msg, prettify=False):
    if prettify: pretty(msg, level=MESSAGE)
    else: write(msg, level=MESSAGE)

def detail(msg, prettify=True):
    if prettify: pretty(msg, level=DETAIL)
    else: write(msg, level=DETAIL)

def die(msg, prettify=False):
    if prettify: pretty(msg, level=DISASTER)
    else: write(msg, level=DISASTER)
    if deathThrows: raise Exception(msg)


