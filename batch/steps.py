#! /usr/bin/python
import sys
import os
import re
import math

# functions for creating and managing the step sequences that drive
# a simulation run, and reading & writing the corresponding files
# taken as input by the C implementation

# (might also read & convert input files from BRAINCIRC, if I can be bothered)

# read a BCMD input file and create the corresponding step sequence
# returns the sequence plus a list of any format errors encountered
def readSequence ( file ):
    steps = []
    time = 0
    count = 0
    errs = []
    setfields = []
    outfields = ['*']
    detfields = ['*']
    outhead = True
    dethead = True
    
    # the C parser requires that the step count is specified before anything
    # other than comments -- so keep track of anyting other than comments happening
    anything = False
    
    with open(file) as f:
        linecount = 0
        for line in f:
            linecount = linecount + 1
            
            # dispense with cases that don't need tokenisation first
            if line.startswith('#') or len(line.strip())==0:
                continue
            
            if line.startswith('!'):
                anything = True
                if line.startswith('!!!'):
                    dethead = True
                    outhead = True
                elif line.startswith('!!'):
                    dethead = True
                elif line.startswith('!0'):
                    outhead = False
                    dethead = False
                else:
                    outhead = True
                continue
            
            # remaining cases all need tokenising
            tokens = line.split()
            
            # output fields
            if line.startswith('>'):
                anything = True
                if len(tokens) == 1:
                    errs.append('incomplete output spec at line %d: "%s" (treating as 0)' % (linecount, line))
                    fields = []
                elif tokens[1] == '*':
                    fields = ['*']
                elif tokens[1].isdigit():
                    fields = tokens[2:]
                    if len(fields) != int(tokens[1]):
                        errs.append('incorrect field count in output spec at line %d: "%s" (inferring)' % (linecount, line))
                else:
                    errs.append('no field count in output spec at line %d: "%s" (inferring)' % (linecount, line))
                
                if tokens[0] == '>':
                    outfields = fields
                elif tokens[0] == '>>':
                    detfields = fields
                else:
                    outfields = fields
                    detfields = fields
                    if tokens[0] != '>>>':
                        errs.append('invalid output spec at line %d: "%s" (treating as ">>>")' % (linecount, line))
            
            elif line.startswith('@'):
                if count > 0:
                    errs.append('extra step count declaration at line %d: "%s" (ignoring)' % (linecount, line))
                    continue
                elif anything:
                    errs.append('step count declaration is not first command in file at line %d: "%s"' % (linecount, line))
                if len(tokens) < 2:
                    errs.append('missing step count at line %d: "%s"' % (linecount, line))
                    continue
                elif len(tokens) > 2:
                    errs.append('too many tokens in step count declaration at line %d: "%s" (discarding excess)' % (linecount, line))
                if tokens[1].isdigit():
                    count = int(tokens[1])
                else:
                    errs.append('invalid step count at line %d: "%s"' % (linecount, line))
                    
            elif line.startswith(':'):                
                anything = True
                if len(tokens) < 2:
                    errs.append('empty field spec at line %d: "%s" (treating as 0)' % (linecount, line))
                    setfields = []
                elif not tokens[1].isdigit():
                    errs.append('invalid field count at line %d: "%s" (inferring)' % (linecount, line))
                    setfields = tokens[1:]
                else:
                    setfields = tokens[2:]
                    if len(setfields) != int(tokens[1]):
                        errs.append('incorrect field count at line %d: "%s" (inferring)' % (linecount, line))
            
            elif line.startswith('='):
                anything = True
                if len(tokens) < 3:
                    errs.append('empty/incomplete absolute step at line %d: "%s" (skipping)' % (linecount, line))
                    continue

                if len(tokens) != len(setfields) + 3:
                    # TODO: possibly try to handle this more helpfully
                    errs.append('wrong number of tokens in absolute step at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                    
                try:
                    start = float(tokens[1])
                    end = float(tokens[2])
                except ValueError:
                    errs.append('invalid time value for absolute step at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                try:
                    assigns = [float(f) for f in tokens[3:]]
                except ValueError:
                    # TODO: again, could maybe be more helpful about this?
                    errs.append('invalid field value for absolute step at line %d: "%s" (skipping)' % (linecount, line))
                
                steps.append( {'type':'=', 'n':1, 'start':start, 'end':end,
                               'duration':end - start,
                               'setfields':setfields, 'setvalues': assigns,
                               'outfields':outfields, 'detfields':detfields,
                               'outhead':outhead, 'dethead':dethead} )
                outhead = False
                dethead = False
                time = end
                
            elif line.startswith('+'):
                anything = True
                if len(tokens) < 2:
                    errs.append('missing relative time step at line %d: "%s" (skipping)' % (linecount, line))
                    continue

                if len(tokens) != len(setfields) + 2:
                    # TODO: possibly try to handle this more helpfully
                    errs.append('wrong number of tokens in relative step at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                    
                try:
                    duration = float(tokens[1])
                except ValueError:
                    errs.append('invalid duration for relative step at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                try:
                    assigns = [float(f) for f in tokens[2:]]
                except ValueError:
                    # TODO: again, could maybe be more helpful about this?
                    errs.append('invalid field value for relative step at line %d: "%s" (skipping)' % (linecount, line))
                
                steps.append( {'type':'+', 'n':1, 'start':time, 'end':time + duration,
                               'duration':duration,
                               'setfields':setfields, 'setvalues': assigns,
                               'outfields':outfields, 'detfields':detfields,
                               'outhead':outhead, 'dethead':dethead} )
                outhead = False
                dethead = False
                time = time + duration
                
            elif line.startswith('*'):
                anything = True
                if len(tokens) < len(setfields) + 3:
                    errs.append('wrong number of tokens in multi-step spec at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                try:
                    reps = int(tokens[1])
                except ValueError:
                    errs.append('invalid rep count in multi-step spec at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                try:
                    duration = float(tokens[2])
                except ValueError:
                    errs.append('invalid time step value in multi-step spec at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                try:
                    increments = [float(f) for f in tokens[3:]]
                except ValueError:
                    errs.append('invalid field increment in multi-step spec at line %d: "%s" (skipping)' % (linecount, line))
                    continue
                
                steps.append( {'type':'*', 'n':reps, 'start':time, 'end':time + reps * duration,
                               'duration':duration,
                               'setfields':setfields, 'setvalues': increments,
                               'outfields':outfields, 'detfields':detfields,
                               'outhead':outhead, 'dethead':dethead} )
                outhead = False
                dethead = False
                time = time + reps * duration
                
            else:
                errs.append('unrecognised line type at line %d: "%s"' % (linecount, line))
        
        inferred = sum([s['n'] for s in steps])
        if count == 0:
            errs.append('no valid step count in input, inferred count is %d' % inferred)
        elif count != inferred:
            errs.append("declared count %d doesn't match inferred count %d" % (count, inferred))
    
    return steps, errs

# write step sequence to a file
# we ensure that the output syntax is correct and the file is
# self-consistent, but don't properly validate the semantics or
# attempt to do any compression -- if that's to happen it should
# be elsewhere
def writeSequence ( seq, filename=False, comment='' ):
    # default state
    setfields = None
    outfields = ['*']
    detfields = ['*']
    assigned = False
    outhead = True
    dethead = True

    if filename:
        file = open(filename, 'w')
    else:
        file = sys.stdout
    
    file.write('# BCMD input file generated by writeSequence\n')
    if comment:
        file.write('# %s\n' % str(comment))
    
    count = sum([s['n'] for s in seq])
    file.write('@ %d\n' % count)
    
    for step in seq:
        # make sure the set and output fields are correct
        if step['outfields'] != outfields:
            outfields = step['outfields']
            if outfields == step['detfields']:
                detfields = step['detfields']
                file.write('>>> ')
            else:
                file.write('> ')
            if len(outfields) and outfields[0] == '*':
                file.write('*\n')
            else:
                file.write('%d %s\n' % (len(outfields), " ".join(outfields)))
        elif step['detfields'] != detfields:
            detfields = step['detfields']
            if len(detfields) and detfields[0] == '*':
                file.write('>> *\n')
            else:
                file.write('>> %d %s\n' % (len(detfields), " ".join(detfields)))
    
        # this is a bit laborious to make the results concise
        # (the converse would be possible, but wrong)
        if step['outhead'] != outhead or step['dethead'] != dethead:
            if step['outhead'] == step['dethead']:
                if step['outhead']:
                    file.write('!!!\n')
                else:
                    file.write('!0\n')
            elif step['outhead']:
                if dethead:
                    file.write('!0\n')
                file.write('!\n')
            else:
                if outhead:
                    file.write('!0\n')
                file.write('!!\n')
        outhead = False
        dethead = False
        
        if step['setfields'] != setfields:
            setfields = step['setfields']
            file.write(': %d %s\n' % (len(setfields), " ".join(setfields)))
            assigned = False
        
        # now write the actual step
        if step['type'] == '=':
            assigned = True
            file.write('= %g %g %s\n' % (step['start'], step['end'],
                                         " ".join([("%g" % x) for x in step['setvalues']])))
        elif step['type'] == '+':
            file.write('+ %g %s\n' % (step['duration'],
                                      " ".join([("%g" % x) for x in step['setvalues']])))
        elif step['type'] == '*':
            if not assigned:
                print >> sys.stderr, "Warning: multi-step specified for fields without previous assignment"
            file.write('* %d %g %s\n' % (step['n'], step['duration'],
                                         " ".join([("%g" % x) for x in step['setvalues']])))
        else:
            # unknown step type, shouldn't happen but...
            print >> sys.stderr, 'Unknown step type: %s' % step['type']
    
    if filename:
        file.close()

# create a version of a step sequence containing only explicit, absolute steps
# (if the supplied sequence does not include any relative steps, it is returned as is)
def explicit(seq):   
    if sum([(s['type'] != '=') for s in seq]) == 0:
        return seq
    
    setfields = []
    setvals = {}
    time = 0
    
    result = []
    for step in seq:
        if step['type'] != '*':
            # update current field values
            setfields = step['setfields']
            for ii in range(len(setfields)):
                setvals[setfields[ii]] = step['setvalues'][ii]
            time = step['end']
        
        # easy ones
        if step['type'] == '=':
            result.append(step)
        elif step['type'] == '+':
            dupe = step.copy()
            dupe['type'] = '='
            result.append(dupe)
        
        # expand to multiple steps with incremental values
        elif step['type'] == '*':
            setfields = step['setfields']
            for ii in range(step['n']):
                dupe = step.copy()
                dupe['type'] = '='
                dupe['start'] = time
                time = time + dupe['duration']
                dupe['end'] = time
                if ii:
                    dupe['dethead'] = False
                    dupe['outhead'] = False
                dupe['setvalues'] = []
                for jj in range(len(setfields)):
                    setvals[setfields[jj]] = setvals.get(setfields[jj], 0) + step['setvalues'][jj]
                    dupe['setvalues'].append(setvals[setfields[jj]])
                
                result.append(dupe)
    
    return result

# read a BRAINCIRC input file -- adapted from Tracy's ABC code
# (this only parses the generic format, it does not attempt to interpret
# the content)
def readBraincirc(file):
    comment = '//'
    startData = re.compile(r'\*{6,}')
    indata = False
    header = {}
    pvals = {}
    data = []
    
    with open(file) as f:
        for line in f:
            line = line.strip('\t\n\r ')
            
            if not line or line.startswith(comment):
                continue
            
            if indata:
                data.append([float(d) for d in line.split()])
                
            elif startData.match(line):
                indata = True
            
            elif ':' in line:
                div = line.split(':')
                field = div[0].strip()
                values = [s.strip() for s in div[1].split(',')]
                header[field] = values
            
            else:
                # try interpreting as a pvals file
                div = line.split()
                try:
                    pvals[div[0]] = float(div[1])
                except (ValueError, KeyError):
                    print >> sys.stderr, 'Unable to interpret line: "%s" (skipping)' % line
    
    return { 'header': header, 'data':data, 'pvals':pvals }

# convert a BRAINCIRC input file to a step sequence
# (this msotly just defers to the appropriate auxiliary functions)
def braincircToSequence ( bc ):
    seq = makePvalsStep(bc['pvals'])
    seq += makeResetSequence(bc['header'].get('reset', None))
    seq += makeSteadySequence(bc['header'].get('steady', None))
    
    if 'min_val' in bc['header']:
        seq += makeAutoregSequence(bc)
    else:
        seq += makeNormalSequence(bc)
    
    return seq

# directly set parameter values if required
def makePvalsStep ( pvals ):
    if len(pvals):
        return [{'type':'=', 'n':1, 'start':0, 'end':0,
                 'duration':0, 'setfields':pvals.keys(), 'setvalues':pvals.values(),
                 'outfields':[], 'detfields':[],
                        'outhead':False, 'dethead':False}]
    else:
        return []

# convert a normal BRAINCIRC input file to a step sequence
def makeNormalSequence ( bc, time=0, outfields=['*'], detfields=['*'], outhead=True, dethead=True ):
    seq = []
    params = bc['header'].get('chosen_param', None)
    timestep = bc['header'].get('time_step', None)
    
    if not params:
        return seq
    
    if ( timestep ):
        timestep = float(timestep[0])
        for row in bc['data']:
            if len(row) != len(params):
                print >> sys.stderr('Data row length does not match declared parameters')
            seq.append({'type':'=', 'n':1, 'start':time, 'end':time + timestep,
                        'duration':timestep, 'setfields':params, 'setvalues':row,
                        'outfields':outfields, 'detfields':detfields,
                        'outhead':outhead, 'dethead':dethead})
            time = time + timestep
            outhead = False
            dethead = False
    else:
        for row in bc['data']:
            duration = float(row[0])
            if len(row) != len(params) + 1:
                print >> sys.stderr('Data row length does not match declared parameters')
            seq.append({'type':'=', 'n':1, 'start':time, 'end':time + duration,
                        'duration':timestep, 'setfields':params, 'setvalues':row[1:],
                        'outfields':outfields, 'detfields':detfields,
                        'outhead':outhead, 'dethead':dethead})
            time = time + duration
            outhead = False
            dethead = False
    
    return seq

# convert a BRAINCIRC autoregulation input to a step sequence
def makeAutoregSequence ( bc, begin=0, outfields=['*'], detfields=['*'],  outhead=True, dethead=True):
    seq = []
    
    param = bc['header'].get('chosen_param', None)
    start = bc['header'].get('init_vals', [0])
    step = bc['header'].get('step_vals', [1])
    timestep = bc['header'].get('time_step', [1])
    bottom = bc['header'].get('min_val', None)
    top = bc['header'].get('max_val', None)
    
    if param and bottom and top:
        start = float(start[0])
        step = float(step[0])
        timestep = float(timestep[0])
        bottom = float(bottom[0])
        top = float(top[0])
        
        down = math.floor((start - bottom)/step)
        up = math.floor((top - bottom)/step)
        
        seq.append({'type':'=', 'n':1, 'start':begin, 'end':begin + timestep,
                    'duration':timestep, 'setfields':param, 'setvalues':[start],
                    'outfields':outfields, 'detfields':detfields,
                    'outhead':outhead, 'dethead':dethead})
        
        begin = begin + timestep
        seq.append({'type':'*', 'n':down, 'start':begin, 'end':begin + down * timestep,
                    'duration':timestep, 'setfields':param, 'setvalues': [-step],
                    'outfields':outfields, 'detfields':detfields,
                    'outhead':False, 'dethead':False})
        begin = begin + down * timestep
        seq.append({'type':'*', 'n':up, 'start':begin, 'end':begin + up * timestep,
                    'duration':timestep, 'setfields':param, 'setvalues': [step],
                    'outfields':outfields, 'detfields':detfields,
                    'outhead':False, 'dethead':False})
    else:
        print >> sys.stderr, 'Invalid autoreg spec -- sequence not produced'
    return seq

# generate a BRAINCIRC reset sequence -- specified parameters are
# interpolated (in parallel) from the specified start values to the
# specified end values, without generating any output
def makeResetSequence ( reset, timestep=1000, stepcount=100, end=0 ):
    seq = []
    if reset and len(reset) > 2:
        setfields = []
        startvals = []
        endvals = []
        
        ii = 0
        while ii + 3 <= len(reset):
            setfields.append(reset[ii])
            startvals.append(float(reset[ii+1]))
            endvals.append(float(reset[ii+2]))
            ii += 3
        
        increments = [(endvals[ii] - startvals[ii])/stepcount for ii in range(len(startvals))]
        
        duration = stepcount * timestep
        start = end - duration
        
        seq.append({'type':'=', 'n':1, 'start':start, 'end':start + timestep,
                    'duration':timestep, 'setfields':setfields, 'setvalues':startvals,
                    'outfields':[], 'detfields':[],
                    'outhead':False, 'dethead':False})
        seq.append({'type':'*', 'n':stepcount - 1, 'start':start + timestep, 'end':end,
                    'duration':timestep, 'setfields':setfields, 'setvalues':increments,
                    'outfields':[], 'detfields':[],
                    'outhead':False, 'dethead':False})
                    
    return seq

# generate a steadying period
def makeSteadySequence ( steady, duration=1000, end=0 ):
    if steady == 'none':
        return []
    else:
        return [{'type':'=', 'n':1, 'start':end-duration, 'end':end,
                 'duration':duration, 'setfields':[], 'setvalues':[],
                 'outfields':[], 'detfields':[],
                 'outhead':False, 'dethead':False}]

# read multiple source files and generate a concatenated step sequence
def readFiles ( files, errout=None ):
    combo = []
    sources = []
    
    for file in files:
        if ( errout ):
            print >> errout, 'Attempting to process file %s' % file
    
        if file.endswith('.input'):
            steps, errs = readSequence(file)
    
            if errout and len(errs) > 0:
                print >> errout, 'Errors found in input:\n'
                for err in errs:
                    print >> errout, err
        
        elif file.endswith('.dat'):
            steps = braincircToSequence(readBraincirc(file))
        
        # don't know about any other file types at present
        else: continue
        
        if steps:
            combo += steps
            sources.append(file)
        elif errout:
            print >> errout, '%f produced no result' % file      
    
    return combo, sources

# generate a simple parameter-setting sequence with no output and
# no duration using values provided by abc-sysbio
def abcParamSequence ( names, values ):
    pnames = [ names[ii] for ii in range(len(values)) if values[ii] is not None ]
    pvals = [ x for x in values if x is not None ]        
    return[{ 'type':'=', 'n':1, 'start':0, 'end':0,
             'duration':0, 'setfields':pnames, 'setvalues':pvals,
             'outfields':[], 'detfields':[],
             'outhead': False, 'dethead':False }]

# generate an input sequence from the specifications used by our
# abc-sysbio wrapper functions -- assumes that we will use only
# the coarse output file, and include headers
def abcAbsoluteSequence ( times, abcInputs, abcOutputs, start=None, outhead=True, steady=1000 ):
    seq = []
    if start is None:
        if len(times) > 1:
            start = times[0] - (times[1] - times[0])
        else:
            start = 0
    
    setfields = [ x['name'] for x in abcInputs ]
    outfields = [ x['name'] for x in abcOutputs ]
    
    if ( steady ):
        seq.append( { 'type': '=', 'n':1, 'start':start-steady,
                      'end': start, 'duration': steady,
                      'setfields':setfields,
                      'setvalues': [ x['points'][0] for x in abcInputs ],
                      'outfields': [], 'detfields':[],
                      'outhead': False, 'dethead':False } )
    
    for ii in range(len(times)):
        seq.append( { 'type': '=', 'n': 1, 'start': start,
             'end': times[ii], 'duration': times[ii]-start,
             'setfields': setfields,
             'setvalues': [ x['points'][ii] for x in abcInputs ],
             'outfields': outfields, 'detfields':[],
             'outhead': outhead, 'dethead':False } )
        outhead = False
        start = times[ii]
    
    return seq

# run file directly to test input parser
if __name__ == '__main__':
    import pprint
    
    if sys.argv[1] == '-d':
        dump_tree = True
        combo, sources = readFiles(sys.argv[2:], sys.stderr)
    else:
        combo, sources = readFiles(sys.argv[1:], sys.stderr)
        dump_tree = False
    
    if combo:
        print >> sys.stderr, '%d steps' % sum([s['n'] for s in combo])
        if dump_tree:
            print >> sys.stderr, '\n------\n\n' + pprint.pformat(combo)
        print >> sys.stderr, '\n------\nPrinting sequence to stdout'
        writeSequence(combo, comment='from: ' + ', '.join(sources))
