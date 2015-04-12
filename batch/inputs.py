#! /usr/bin/python
# functions to import data from various input file formats
# for use as imports to our ABC (and possibly other) jobs

import sys, os, os.path
import csv

# this is a nasty hack whereby we guarantee that there will be no
# collision between a time field imported from a braincirc input
# file and any 't' variable it contains -- since we strip whitespace
# from those names...
LOCAL_TIME = ' t'

# plausible input types to support:
#
#   csv, txt ...
#   braincirc
#   bcmd input
#

# utility to convert to a string to float if possible
# otherwise leave as string
def float_or_str(s):
    try:
        return float(s)
    except ValueError:
        return s

# attempt to read a CSV/TXT file as a dictionary, keyed by the header names
# columns are lists, converted into floats where possible, otherwise left as strings
def readCSV(filename, wrap_timeseries=True, default_dialect=csv.excel_tab):
    result = {}
    
    with open(filename, 'rU') as f:
        try:
            dialect = csv.Sniffer().sniff(f.read(1024), delimiters='\t,;')
        except csv.Error as e:
            #print e
            dialect = default_dialect
            
        f.seek(0)
        
        dr = csv.DictReader(f, dialect=dialect)
        
        for row in dr:
            for kk in row.keys():
                val = float_or_str(row[kk])
                
                if kk in result:
                    result[kk].append(val)
                else:
                    result[kk] = [val]
    
    if wrap_timeseries:
        return {'timeseries': result}
    else:
        return result

# attempt to read a braincirc input file
# this is closely based on the equivalent function in steps.py, and
# eventually I'll try to unify the two, but for the moment the
# outputs are a bit different (as is the intent)
# (we optionally also support bcmd-style comments, since that doesn't really conflict)
def readBraincirc(filename, bcmd_comments=True):
    indata = False
    header = {}
    pvals = {}
    data = []
    timeseries = {}
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip('\t\n\r ')
            
            if not line or line.startswith('//') or (bcmd_comments and line.startswith('#')):
                continue
            
            if indata:
                data.append([float(d) for d in line.split()])
                
            elif line.startswith('******'):
                indata = True
            
            elif ':' in line:
                div = line.split(':')
                field = div[0].strip()
                values = [s.strip() for s in div[1].split(',')]
            
                # NB: for consistency values list is wrapped in another list
                # so that we can cope with multiple matching declarations
                # (as in Tracy's ABC input format)
                if field in header:
                    header[field].append(values)
                else:
                    header[field] = [values]
            
            else:
                # try interpreting as a pvals file
                div = line.split()
                try:
                    pvals[div[0]] = float(div[1])
                except (ValueError, KeyError):
                    print >> sys.stderr, 'Unable to interpret line: "%s" (skipping)' % line
    
    # for input files doing stepwise parameter assignments, attempt to transpose data
    # into a dictionary with a vector of values for each field, like the CSV input
    if data and 'chosen_param' in header:
        if 'time_step' in header:
            tt = float(header['time_step'][0][0])
            timeseries[LOCAL_TIME] = [x * tt for x in range(len(data))]
            tsnames = header['chosen_param'][0]
        else:
            # time steps are being specified explicitly
            tsnames = [LOCAL_TIME] + header['chosen_param']
        
        for name in tsnames: timeseries[name] = []
        
        for row in data:
            for ii in range(len(tsnames)):
                if ii > len(row):
                    timeseries[tsnames[ii]].append('NA')
                else:
                    timeseries[tsnames[ii]].append(row[ii])
    
    return { 'header': header, 'data':data, 'pvals':pvals, 'timeseries':timeseries }

# despatch to relevant file reader based on file extension
# (might get more sophisticated later, but probably won't)
def readFile(name, wrap_csv=True):
    if name.lower().endswith('.dat') or name.lower().endswith('job'):
        return readBraincirc(name)
    if name.lower().endswith('.csv') or name.lower().endswith('.txt') or name.lower().endswith('.out'):
        return readCSV(name, wrap_csv)
    
    # that's all we know about so far...
    return 'Unknown type for file: %s' % name

# slightly more purposeful reader, that explicitly wants a key-value pairs result,
# for CSV/TXT files, allows by-row and by-column ordering
# for DAT files, header and pvals sections are merged, but we don't support list values,
# so any items beyond first are discarded
# result is a straight dictionary with string keys & values converted to float where possible
# (and optionally omitted if not)
def readValues(name, float_only=True):
    result = {}
    if name.lower().endswith('.dat') or name.lower().endswith('job'):
        data = readBraincirc(name)
        if data['header']:
            # unwrap header values and convert to float if possible
            for name in data['header']:
                val = float_or_str(data['header'][name][0])
                if isinstance(val, float) or not float_only:
                    result[name] = val
                
        # pvals override header if both are present
        result.update(data['pvals'])
    
    elif name.lower().endswith('.csv') or name.lower().endswith('.txt'):
        data = readCSV(name, wrap_timeseries=False)
        
        # we're going to apply a thoroughly horrible heuristic here: if there are two columns,
        # then we have to check whether the data is row-oriented
        if len(data) == 2:
            # if it is, then one of the column headers should actually be a float,
            # and we need to include that as one of our result values
            names = []
            try:
                topval=float(data.keys()[0])
                result[data.keys()[1]] = topval
                names = data[data.keys()[1]]
                vals = data[data.keys()[0]]
            except ValueError:
                try:
                    topval=float(data.keys()[1])
                    result[data.keys()[0]] = topval
                    names = data[data.keys()[0]]
                    vals = data[data.keys()[1]]
                except ValueError:
                    # nope, so let's just drop through to the column-oriented case
                    pass
            
            # transpose the rest of the column contents
            for ii in range(len(names)):
                val = float_or_str(vals[ii])
                if isinstance(val, float) or not float_only:
                    result[str(names[ii])] = val
        
        if not result:
            # assume file is organised by column
            # data should already be in the right
            # order, but we need to unwrap, convert and possibly drop non-floats
            for name in data:
                val = float_or_str(data[name][0])
                if isinstance(val, float) or not float_only:
                    result[name] = val

    return result
    

# testing, testing, 1, 2, 1, 2, 2, 2, 1, 2...
if __name__ == '__main__':
    import pprint
    
    for file in sys.argv[1:]:
        pprint.pprint(readFile(file))
