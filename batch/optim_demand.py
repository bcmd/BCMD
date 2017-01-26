# Import optim submodule
import optim
import os
import argparse
import copy
import pprint

# environment
VERSION = 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.relpath('../build', HERE))
INFO = 'optim.info'

# defaults
JOB_MODE = 'GLP'
SOLVER = 'galileo'
PARAM_SELECT = '*'
DISTANCE = 'euclidean'
MAX_ITER = 1e3
STEADY = 1000

CONFIG_DEFAULT = {'build': BUILD,
                  'work': None,
                  'info': INFO,
                  'job_mode': JOB_MODE,
                  'solver': SOLVER,
                  'nbatch': 1,  # don't support parallel execution at present
                  'beta': 1,  # ditto
                  'param_select': PARAM_SELECT,
                  'weights': {},
                  'timestep': None,
                  'sigma': None}

# process command-line arguments


def process_args():
    """
    Function to process command line arguments.
    Defaults are drawn from global variable CONFIG.
    :return: Updated config dictionary.
    """

    ap = argparse.ArgumentParser(
        description="Parameter optimisation for BCMD models")
    ap.add_argument(
        '-b', '--build',
        help='build/model directory (default: [BCMD_HOME]/build)',
        metavar='DIR')
    ap.add_argument(
        '-o', '--outdir',
        help='output directory (default:[BUILD]/[MODEL_NAME]/[TIMESTAMP]',
        metavar='DIR')
    ap.add_argument(
        '-d', '--dryrun',
        help='dump configuration details without simulating',
        action='store_true')
    ap.add_argument(
        '-w', '--wetrun',
        help='single test run and data dump without full optimisation',
        action='store_true')
    ap.add_argument(
        '-D', '--debug',
        help='run in debug mode, logging various things to stderr',
        action='store_true')
    ap.add_argument('jobfile', help='optjob specification file')
    ap.add_argument('rootdir', help='Directory containing the datafiles')

    args = ap.parse_args()

    config = copy.copy(CONFIG_DEFAULT)
    config['rootdir'] = args.rootdir
    inputDir = os.path.join(config['rootdir'], 'input_files')
    config['inputfiles'] = [os.path.join(inputDir, f) for f in os.listdir(inputDir) if os.path.isfile(os.path.join(inputDir, f))]
    config['jobfile'] = args.jobfile

    if args.build:
        config['build'] = args.build
    else:
        config['build'] = BUILD

    if args.outdir:
        config['work'] = args.outdir
    # otherwise leave as None and concoct after reading job file

    config['dryrun'] = args.dryrun
    config['wetrun'] = args.wetrun
    config['debug'] = args.debug

    return config


def datafile_append(config):
    # Begin by clearing the old datafile
    config['datafile'] = None
    if config['debug']:
        print(config['inputfiles'])
    config['datafile'] = config['inputfiles'].pop(0)
    return config


def looped_process(config):
    while len(config['inputfiles']) != 0:
        datafile_append(config)
        if config:
            optim.process_inputs(config)
            model = optim.make_model(config)
            optimiser = optim.make_optimiser(config, model)
            if optimiser:

                rr = optim.optimise(config, model, optimiser)

                # for the moment we just print the results here
                # -- which may be superfluous, since OO will print stuff as well
                print("\n~~ Output from file %s\n" % config['datafile'])
                print("\nRESULTS\n")
                print("Stop case %g: %s" % (rr.istop, rr.msg))
                if rr.isFeasible:
                    print("Feasible solution found")
                else:
                    print("No feasible solution found")
                print("&& Final distance value: %f" % rr.ff)
                print("Final parameter values:")
                for ii in range(len(rr.xf)):
                    print("^^  %s: %f" % (config['params'][ii]['name'], rr.xf[ii]))

            else:
                print('CONFIG:')
                pprint.pprint(config)

if __name__ == '__main__':
    config = process_args()
    looped_process(config)
