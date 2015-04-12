# as usual, brutally hacked down from the ASB original

import os, os.path
import sys, pickle
import numpy

class input_output:
    
    def __init__(self, folder):
        self.folder = os.path.abspath(folder)

    # write rates, distances, trajectories    
    def write_data(self, population, results, timing, models, data):
        
        beta = len(results.trajectories[0])
        
        with open(os.path.join(self.folder, 'rates.txt'),"a") as rate_file:
            print >> rate_file, population+1, results.epsilon, results.sampled, results.rate, round(timing,2)

        # distances are stored as [nparticle][nbeta][d1, d2, d3 .... ]
        with open(os.path.join(self.folder, 'distance_Population_%d.txt' % (population + 1)), 'a') as distance_file:
            for i in range(len(results.distances)):
                for j in range(len(results.distances[i])):
                    print >> distance_file, i+1, j, results.distances[i][j], results.models[i]

        # trajectories are stored as [nparticle][nbeta][ species ][ times ]
        with open(os.path.join(self.folder, 'traj_Population_%d.txt' % (population + 1)), 'a') as traj_file:
            for i in range(len(results.trajectories)):
                for j in range(len(results.trajectories[i])): 
                    arr = results.trajectories[i][j]
                    nrow, ncol = numpy.shape( arr )
                    for ic in range(ncol):
                        print >> traj_file, i, j, results.models[i], ic, 
                        for ir in range(nrow):
                            print >> traj_file, arr[ir,ic],
                        print >> traj_file, ""

        if len(results.margins) > 1:
            with open(os.path.join(self.folder, 'ModelDistribution.txt'), 'a') as model_file:
                for m in results.margins: 
                    print >> model_file, m,
                print >> model_file, ""

        nmodels = len(models)
        for mod in range(nmodels):
            popfolder = os.path.join(self.folder, 'results_' + models[mod].name, 'Population_%d' % (population + 1))
            print >> sys.stderr, 'attempting to create population results folder %s' % popfolder
            try:
                os.makedirs(popfolder)
            except EnvironmentError as e:
                print >> sys.stderr, e

        # count number of particles in each model so that we can skip empty models
        counts = numpy.zeros([nmodels])
        nparticles = len(results.weights)
        for np in range(nparticles):
            counts[ results.models[np] ] = counts[ results.models[np] ] + 1
            

        # print out particles and weights if there are particles
        for mod in range(nmodels):
            if counts[mod] > 0:
                popfolder = os.path.join(self.folder, 'results_' + models[mod].name, 'Population_%d' % (population + 1))
                weightname = os.path.join(popfolder, 'data_Weights_%d.txt' % (population + 1))
                paramname = os.path.join(popfolder, 'data_Population_%d.txt' % (population + 1))
                with open(weightname, 'w') as weight_file, open(paramname, 'w') as param_file:
                    nparticles = len(results.weights)
                    for g in range(nparticles):
                        if( results.models[g] == mod ):
                            for k in range(len(results.parameters[g])):
                                print >> param_file, results.parameters[g][k],
                            print >> param_file, ""

                            print >>weight_file, results.weights[g]


    # write trajectories and parameters from simulations    
    def write_data_simulation(self, population, results, timing, models, data):

        nparticles = len(results.trajectories)
        beta = len(results.trajectories[0])

        # trajectories are stored as [nparticle][nbeta][ species ][ times ]
        with open(os.path.join(self.folder, 'trajectories.txt'), 'a') as traj_file:
            for i in range(nparticles):
                for j in range(beta): 
                    arr = results.trajectories[i][j]
                    nrow, ncol = numpy.shape( arr )
                    for ic in range(ncol):
                        print >> traj_file, i, j, results.models[i], ic, 
                        for ir in range(nrow):
                            print >> traj_file, arr[ir,ic],
                        print >> traj_file, ""

        # dump out all the parameters
        with open(os.path.join(self.folder, 'particles.txt'), 'a') as param_file:
            for i in range(nparticles):
                print >> param_file, i, results.models[i],
                for j in results.parameters[i]:
                    print >> param_file, j,
                print >> param_file, ""
                        
    # create output folders
    def create_output_folders(self, modelnames, numOutput, pickling):
        
        try:
            os.makedirs(self.folder)
        except EnvironmentError as e:
            print >> sys.stderr, e

        for mod in modelnames:
            try:
                os.makedirs(os.path.join(self.folder, 'results_' + mod))
            except EnvironmentError as e:
                print >> sys.stderr, e

        if pickling:
            dupe = os.path.join(self.folder, 'copy')
            try:
                os.makedirs(dupe)
            except EnvironmentError as e:
                print >> sys.stderr, e
            
            with open(os.path.join(dupe, 'algorithm_parameter.pickled'), 'w') as out_file:
                pickle.dump(numOutput, out_file)


    # read the stored data
    # note: in the current regime this never gets called
    # however abcsmc does *write* the files, so we *could* read them if necessary
    def read_pickled(self, location):
        # pickle numbers selected model of previous population
        # pickle population of selected model of previous population pop_pickled[selected_model][n][vectpos]
        # pickle weights of selected model of previous population weights_pickled[selected_model][n][vectpos]

        with open(os.path.join(location, 'copy', 'model_last.pickled'), 'r') as in_file:
            model=pickle.load(in_file)
        
        with open(os.path.join(location, 'copy', 'weights_last.pickled'), 'r') as in_file:
            weights=pickle.load(in_file)

        with open(os.path.join(location, 'copy', 'params_last.pickled'), 'r') as in_file:
            params=pickle.load(in_file)

        with open(os.path.join(location, 'copy', 'margins_last.pickled'), 'r') as in_file:
            margins=pickle.load(in_file)

        with open(os.path.join(location, 'copy', 'kernels_last.pickled'), 'r') as in_file:
            kernels=pickle.load(in_file)

        return [model, weights, params, margins, kernels]

    # write the stored data
    def write_pickled(self, nmodel, model, weights, params, margins, kernels):

        with open(os.path.join(self.folder, 'copy', 'model_last.pickled'), 'w') as out_file:
            pickle.dump(model[:], out_file)

        with open(os.path.join(self.folder, 'copy', 'weights_last.pickled'), 'w') as out_file:
            pickle.dump(weights[:], out_file)

        with open(os.path.join(self.folder, 'copy', 'params_last.pickled'), 'w') as out_file:
            pickle.dump(params, out_file)

        with open(os.path.join(self.folder, 'copy', 'margins_last.pickled'), 'w') as out_file:
            pickle.dump(margins[:], out_file)

        with open(os.path.join(self.folder, 'copy', 'kernels_last.pickled'), 'w') as out_file:
            pickle.dump(kernels[:nmodel], out_file)
