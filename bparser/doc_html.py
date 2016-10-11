# write documentation in HTML format
import sys
import os
import os.path
import re
import datetime, time

# local configuration details
BY_ROW = False
TABLE_COLS = 6

# default stylesheet details
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(THIS_DIR + '/templates')
STYLESHEET = os.path.join(TEMPLATE_DIR, 'bcmd.css')

def writeDoc(model, config):
    with open(os.path.join(config['outdir'], config['html']), 'w') as f:
        printHeader(f, model, config)
        printModelDescription(f, model, config)
        printInputs(f, model, config)
        printOutputs(f, model, config)
        printExternals(f, model, config)
        printTags(f, model, config)
        printDiffs(f, model, config)
        printAlgs(f, model, config)
        printIntermeds(f, model, config)
        printParameters(f, model, config)
        printEmbeds(f, model, config)
        printFooter(f, model, config)
        
def printHeader(file, model, config):
    print >> file, '<html>'
    print >> file, '<head>'
    print >> file, '<title>Model %s Generated Documentation</title>' % config['name']
    
    css = config.get('css-src', None)
    if css is None:
        css = STYLESHEET
    
    if config.get('css-embed', True) and os.path.isfile(css):
        print >> file, '<style media="screen" type="text/css">'
        with open(css) as f:
            for line in f:
                file.write(line)
        print >> file, '\n</style>'
    else:
        print >> file, '<link rel="stylesheet" type="text/css" href="%s" />' % css
    print >> file, '</head>'
    print >> file, '<body>'
    print >> file, '<h1>Model information for %s</h1>' % config['name']

def printModelDescription(file, model, config):
    print >> file, '<div class="overview">'
    print >> file, '<h2>Description</h2>'
    print >> file, '<p>'
    for line in model['modeldocs']:
        if line.startswith('+') or line.startswith('@') or line.startswith('$') or line.startswith('~'):
            pass
        elif line == '':
            print >> file, '</p><p>'
        else:
            print >> file, escape(line)
    print >> file, '</p>'

    print >> file, '<div class="summary">'
    print >> file, '<div>%d state variables ' % len(model['roots'])
    print >> file, '(%d <a href="#section_differential">differential</a>' % len(model['diffs'])
    print >> file, '%d <a href="#section_algebraic">algebraic</a>)' % len(model['algs'])
    print >> file, '</div>'
    
    print >> file, '<div>%d <a href="#section_intermediate">intermediate</a> variables (%d unused)</div>' % (len(model['intermeds']), len([x for x in model['intermeds'] if x in model['unused']]))
    print >> file, '<div>%d <a href="#section_parameters">parameters</a> (%d unused)</div>' % (len(model['params']), len([x for x in model['params'] if x in model['unused']]))
    print >> file, '<div>%d declared <a href="#section_inputs">inputs</a>,' % len(model['inputs'])
    print >> file, '%d default <a href="#section_outputs">outputs</a></div>' % len(model['outputs'])
    print >> file, '%d declared <a href="#section_external">external variables</a></div>' % len(model['extern'])
    print >> file, '<div>%d <a href="#section_tags">tags</a></div>' % len(model['tags'])
    
    if model['embeds']:
        print >> file, '<div>Model includes <a href="#section_embeds">embedded C code</a></div>'
    
    print >> file, '</div>'
    
    print >> file, '<div class="files">'
    print >> file, '<div>Top level source file: <a href="file://%s">%s</a></div>' % (model['sources'][0][0], os.path.basename(model['sources'][0][1]))
    
    if len(model['sources']) > 1:
        print >> file, '<div>The following submodels are imported:</div>'

        items = [ '<a href="file://%s">%s</a>' % (sub[1], sub[0]) for sub in model['sources'][1:] ]
        tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
    else:
        print >> file, '<div>No submodels are imported.</div>'
    
    print >> file, '</div>'

def printTags(file, model, config):
    print >> file, '<div class="tags">'
    print >> file, '<a name="section_tags" />'
    print >> file, '<h2>Tags</h2>'
    
    if model['tags']:
        for tag in sorted(model['tags'].keys(), key=lambda s: s.lower()):
            print >> file, '<div class="tag">'
            print >> file, '<h4><a name="_tag_%s">%s</a></h4>' % (tag, tag)
            items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['tags'][tag], key=lambda s: s.lower()) ]
            tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
            print >> file, '</div>'
    else:
        print >> file, '<p>No tags are defined in this model.</p>'
    
    print >> file, '</div>'

def printInputs(file, model, config):
    print >> file, '<div class="inputs">'
    print >> file, '<a name="section_inputs" />'
    print >> file, '<h2>Inputs</h2>'
    
    if model['inputs']:
        items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['inputs'], key=lambda s: s.lower()) ]
        tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
    else:
        print >> file, '<p>No inputs are declared for this model.</p>'

    print >> file, '</div>'

def printOutputs(file, model, config):
    print >> file, '<div class="outputs">'
    print >> file, '<a name="section_outputs" />'
    print >> file, '<h2>Outputs</h2>'
    
    items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['outputs'], key=lambda s: s.lower()) ]
    tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
    
    print >> file, '</div>'

def printExternals(file, model, config):
    print >> file, '<div class="external">'
    print >> file, '<a name="section_external" />'
    print >> file, '<h2>External Variables</h2>'
    print >> file, '<p>External variables are expected to be defined in some other submodel, which has not been'
    print >> file, 'imported in the present build. Here they will be treated as parameters and default to 0.</p>'
    
    if model['extern']:
        items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['extern'], key=lambda s: s.lower()) ]
        tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
    else:
        print >> file, '<p>No external variables are declared for this model.</p>'
    
    print >> file, '</div>'


# write a list of items as an HTML table, with optional 'decorations' on the tags
# note that the apparent number of columns may be less than specified if filling
# by column (because the last column may be empty)
def tabulate(file, items, ncols, table_decor='', row_decor='', cell_decor='', byrow=False):
    nrows = len(items) // ncols
    leftover = len(items) % ncols
    if leftover > 0:
        nrows = nrows + 1
    
    print >> file, '<div class="tabular">'
    print >> file, '<table %s>' % table_decor
    
    for rr in range(nrows):
        print >> file, '<tr %s>' % row_decor
        
        for cc in range(ncols):
            print >> file, '<td %s>' % cell_decor
            if byrow:
                idx = rr * ncols + cc
            else:
                idx = cc * nrows + rr
            if idx < len(items):
                print >> file, items[idx]
            print >> file, '</td>'
        
        print >> file, '</tr>'
    
    print >> file, '</table>'
    print >> file, '</div>'


def printDiffs(file, model, config):
    print >> file, '<div class="differentials">'
    print >> file, '<a name="section_differential" />'
    print >> file, '<h2>Differential Variables</h2>'
    
    if model['diffs']:
        items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['diffs'], key=lambda s: s.lower()) ]
        tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
    
        for name in sorted(model['diffs'], key=lambda s: s.lower()):
            printVar(name, file, model, config, ['Differential'])
    else:
        print >> file, '<p>This model includes no differential state variables.</p>'
    
    print >> file, '</div>'

def printAlgs(file, model, config):
    print >> file, '<div class="algebraics">'
    print >> file, '<a name="section_algebraic" />'
    print >> file, '<h2>Algebraic Variables</h2>'
    
    if model['algs']:
        items = [ '<a href="#%s">%s</a>' % (name, name) for name in sorted(model['algs'], key=lambda s: s.lower()) ]
        tabulate(file, items, ncols=TABLE_COLS, byrow=BY_ROW)
        
        for name in sorted(model['algs'], key=lambda s: s.lower()):
            printVar(name, file, model, config, ['Algebraic'])
    else:
        print >> file, '<p>This model includes no algebraic state variables.</p>'
    
    print >> file, '</div>'

def printIntermeds(file, model, config):
    print >> file, '<div class="intermediates">'
    print >> file, '<a name="section_intermediate" />'
    print >> file, '<h2>Intermediate Variables</h2>'
    
    if model['intermeds']:
        for name in sorted(model['intermeds'], key=lambda s: s.lower()):
            printVar(name, file, model, config, ['Intermediate'])
    else:
        print >> file, '<p>This model includes no intermediate variables.</p>'
    
    print >> file, '</div>'

def printParameters(file, model, config):
    print >> file, '<div class="parameters">'
    print >> file, '<a name="section_parameters" />'
    print >> file, '<h2>Parameters</h2>'
    
    if model['params']:
        for name in sorted(model['params'], key=lambda s: s.lower()):
            printVar(name, file, model, config, ['Parameter'])
    else:
        print >> file, '<p>This model has no parameters.</p>'
    
    print >>file, '</div>'

def printEmbeds(file, model, config):
    if model['embeds']:
        print >> file, '<div class="embeds">'
        print >> file, '<a name="section_embeds" />'
        print >> file, '<h2>Embedded C Code</h2>'
        
        if model['embeds']:
            print >> file, '<pre>'
            for line in model['embeds']:
                print >> file, line
            print >> file, '</pre>'
        else:
            print >> file, '<p>No embedded C is included in this model.</p>'
        
        print >> file, '</div>'

def printFooter(file, model, config):
    print >> file, '<div class="footer">'
    print >> file, '<p>Generated by <a href="http://tinyurl.com/ucl-bcmd">BCMD</a> module bparser.info</p>'
    print >> file, '<p>%s</p>' % datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print >> file, '</body>'
    print >> file, '</html>'


def printVar(name, file, model, config, classes):
    if name in model['extern']: classes = ['<b>Unsatisfied External</b>']
    if name in model['chemicals']: classes.append('Species')
    if name in model['inputs']: classes.append('Input')
    if name in model['outputs']: classes.append('Output')
    if name in model['unused']: classes.append('Unused')
    
    print >> file, '<div class="symbol">'
    print >> file, '<a name="%s" />' % name
    print >> file, '<h4>%s</h4>' % name

    sym = model['symbols'][name]

    desc = []
    for line in sym['docs']:
        if line.startswith('+') or line.startswith('@') or line.startswith('$') or line.startswith('~'):
            pass
        elif line == '':
            desc.append('</p><p>')
        else:
            desc.append(escape(line))
    
    if desc:
        print >> file, '<div class="description">'
        print >> file, '<p>'
        for line in desc:
            print >> file, line
        print >> file, '</p>'
        print >> file, '</div>'
    
    print >> file, '<div class="classes"><span class="label">Kind:</span> %s</div>' % ', '.join(classes)
    
    if 'units' in sym:
        print >> file, '<div class="units"><span class="label">Units:</span> %s</div>' % sym['units']
    
    if sym['diffs']:
        lhs = "%s'" % name
        deps = set()
        for aux in model['auxiliaries'][name]:
            mass = aux[0]
            if mass < 0:
                mass = -mass
                op = '-'
            else:
                op = '+'
            
            if mass == 1:
                mstr = ''
            else:
                mstr = '%s * ' % str(mass)
            
            lhs = "%s %s %s %s'" % (lhs, op, mstr, aux[1])
            deps |= set([aux[1]])
        expr = '%s = %s' % (lhs, sym['diffs'][0]['expr'])
        deps |= sym['diffs'][0]['depends']
    elif sym['algs']:
        expr = '%s = 0' % sym['algs'][0]['expr']
        deps = sym['algs'][0]['depends']
    else:
        exprs = [x for x in sym['assigns'] if not x['init']]
        if exprs:
            expr = exprs[0]['expr']
            deps = exprs[0]['depends']
        else:
            expr = ''
            deps = []

    if expr:
        print >> file, '<div><span class="label">Expression:</span> %s</div>' % escape(expr)
        
        deps = [ '<a href="#%s">%s</a>' % (x,x) for x in sorted(deps, key=lambda s: s.lower()) ]
        print >> file, '<div><span class="label">Dependencies:</span> %s</div>' % ', '.join(deps)
    
    init = [x for x in sym['assigns'] if x['init']]
    
    if init:
        print >> file, '<div><span class="label">Initialiser:</span> %s</div>' % init[0]['expr']
        if init[0]['depends']:
            ideps = [ '<a href="#%s">%s</a>' % (x,x) for x in sorted(init[0]['depends'], key=lambda s: s.lower()) ]
            print >> file, '<div><span class="label">Initialiser Dependencies:</span> %s</div>' % ', '.join(ideps)
    else:
        print >> file, '<div><span class="label">Initialiser:</span> Not specified, defaults to 0</div>'
        
    if sym['tags']:
        tags = [ '<a href="#_tag_%s">%s</a>' % (x,x) for x in sorted(sym['tags'], key=lambda s: s.lower()) ]
        print >> file, '<div><span class="label">Tags:</span> %s</div>' % ', '.join(tags)

    
    print >> file, '</div>'     # symbol

# currently very crude, to be expanded...
def escape(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text