# execute external commands according to configuration details

import sys, os, os.path
import subprocess
import tempfile

# invoke the BCMD compiler
# returns (result, logfile)
def parse(config):
    args = ['python']
    args.append(os.path.join(config.parser, 'bcmd.py'))
    if config.debug:
        args.extend(['-g', '-v', str(config.debug_verbosity)])
    else:
        args.extend(['-v',  str(config.release_verbosity)])
    
    args.extend(['-p', '-t'])
    args.extend(['-I', os.pathsep.join(config.get_model_path_list())])
    args.extend(['-n', config.model_name])
    args.extend(['-o', config.model_name + config.extensions['model']])
    args.extend(['-d', config.work])
    args.append(os.path.join(config.model_dir, config.model_src))
    logname = os.path.join(config.work, config.model_name + config.extensions['log'])
    with open(logname, 'w') as stderr:
        result = subprocess.call(args, stderr=stderr)
    
    return result, logname

    
# compile the C file
# (this uses make, since the Makefile should have been configured with
# the appropriate compiler details)
def compile(config):
    args = ['make']
    args.append(os.path.join(config.work, config.model_name + config.extensions['model']))
    if not config.debug:
        args.append('DEBUG=0')
    
    # we must execute make in the proper directory
    current = os.getcwd()
    os.chdir(config.home)
    
    stderr = tempfile.TemporaryFile()
    stdout = tempfile.TemporaryFile()
    result = subprocess.call(args, stdout=stdout, stderr=stderr)
    os.chdir(current)
    
    stdout.seek(0)
    out = stdout.read()
    stdout.close()
    
    stderr.seek(0)
    err = stderr.read()
    stderr.close()
    
    return result, out, err

# get info on the compiled model
# TODO: for the moment we assume that the model has been parsed already, should probably check...
# also maybe run the code internally rather than invoking another instance?
def info(config):
    args = ['python']
    args.append(os.path.join(config.parser, 'info.py'))
    args.extend(['-s', '-a'])
    args.extend(['-d', config.work])
    args.append(os.path.join(config.work, config.model_name + config.extensions['parsed']))
    
    stderr = tempfile.TemporaryFile()
    stdout = tempfile.TemporaryFile()
    result = subprocess.call(args, stdout=stdout, stderr=stderr)

    stdout.seek(0)
    out = stdout.read()
    stdout.close()
    
    stderr.seek(0)
    err = stderr.read()
    stderr.close()

    return result, out, err

# invoke GraphViz to make the dependency graph in PDF and GIF formats
# returning the full path to the GIF, or None if graphing failed
def graph(config):
    args = ['dot', '-Tgif']
    gif = os.path.join(config.work, config.model_name + config.extensions['gif'])
    args.extend(['-o', gif])
    args.append(os.path.join(config.work, config.model_name + config.extensions['graphviz']))
    result = subprocess.call(args)
    if result: return None
    
    args = ['dot', '-Tpdf']
    args.extend(['-o', os.path.join(config.work, config.model_name + config.extensions['pdf'])])
    args.append(os.path.join(config.work, config.model_name + config.extensions['graphviz']))
    result = subprocess.call(args)

    return gif


# run the configured model with the configured input and produce
# the configured outputs...
def run(config):
    args = [os.path.join(config.work, config.model_name + config.extensions['model'])]
    args.extend(['-i', os.path.join(config.input_dir, config.input_file)])
    
    if config.coarse:
        args.extend(['-o', os.path.join(config.work, config.coarse_name)])
    
    if config.detail:
        args.extend(['-d', os.path.join(config.work, config.detail_name)])
    
    stderr = os.path.join(config.work, config.model_name + config.extensions['stderr'])
    stdout = os.path.join(config.work, config.model_name + config.extensions['stdout'])
    
    with open(stderr, 'w') as err, open(stdout, 'w') as out:
        result = subprocess.call(args, stderr=err, stdout=out)
    
    return result, stdout, stderr
    