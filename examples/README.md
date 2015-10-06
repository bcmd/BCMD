# Example models and inputs

A number of example files are included with the BCMD distribution,
to demonstrate the workings of the system. These include classic models from
physics and mathematical biology, in addition to some of the brain circulation
models for which the system was specifically devised. Input files are also provided
for most models, though these are usually fairly trivial.

A brief summary of these models is given below, with links to further information where
available.

## BrainSignals

Variations on the simplified model of cerebral blood flow and metabolism first published in [Banaji 2008][1].

* `BrainSignals.modeldef`: a fairly straight port to BCMD of the original BrainSignals formulation.
* `BS.modeldef`: a refactored but not substantively changed version of BrainSignals as used in [Caldwell 2015a][2].
* `B1M2.modeldef`: the best of the further simplified model variants from [Caldwell 2015a][2].

The associated input files can be used with all three model versions:

* `BrainSignals.input`: a very simple synthetic input modelling a step change in the demand parameter *u*.
* `pres.input`: a synthetic input for generating the classic blood pressure autoregulation curve.

Further model variants and input files can be found in the [bsrv](https://github.com/bcmd/bsrv) repository on GitHub.

  [1]: http://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000212
       "Banaji M et al (2008). PLoS Computational Biology, 4(11), e1000212."
  [2]: http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0126695
       "Caldwell M et al (2015). PLoS ONE, 10(5), e0126695–28."


## BrainPiglet

Variations on the expanded model of piglet cerebral blood flow and metabolism
first published in [Moroz 2012][3]. The original version 1.0 model is not (yet)
included, but several subsequent versions are:

* `brainpiglet2.modeldef`: version 2.0, expanded to include cytoplasmic pH and arterial occlusion,
   as published in [Hapuarachchi 2014][4].
* `brainpiglet2-1.modeldef`: version 2.1, extended to include sodium transporters and cytoplasmic
   CO2, developed and used in [Hapuarachchi 2015][5].
* `bp20.modeldef`: the BrainPigletHI variant, based on 2.0, published in [Caldwell 2015b][6]
* `bp20_insult.modeldef`: an optional add-on module for BrainPigletHI, to allow testing
   of different hypotheses concerning non-recovery after hypoxic-ischaemia.

Corresponding inputs are once again very minimal, although the 2.0 input sets a lot of parameters:

* `brainpiglet2.input`
* `brainpiglet2-1.input`

Further input data files for BrainPigletHI can be found in the [bphi](https://github.com/bcmd/bphi) repository on GitHub.

  [3]: http://rsif.royalsocietypublishing.org/cgi/doi/10.1098/rsif.2011.0766
       "Moroz T et al (2012). Journal of The Royal Society Interface, 9(72), 1499–1509."
  [4]: http://www.ncbi.nlm.nih.gov/pmc/articles/PMC4429242/
       "Hapuarachchi T et al (2014). Advances in Experimental Medicine and Biology, 812, 187-194."
  [5]: http://link.springer.com/10.1007/978-1-4939-0620-8_25
       "Hapuarachchi T (2015). PhD thesis, UCL (not yet available online)."
  [6]: http://example.com
       "Caldwell M et all (2015). PLoS ONE, XXXX"

## Cloutier

An adaptation of the cerebral metabolic model from [Cloutier 2009][8].

* `cloutier.modeldef`

In the original model a time-based stimulus is encoded as part of the model definition,
rather than introduced via the inputs. That logic is preserved here, so the input file
does not include a separate stimulus.

* `cloutier.input`

  [8]: http://doi.org/10.1007/s10827-009-0152-8
       "Cloutier M et al (2009). Journal of Computational Neuroscience, 27(3), 391–414."

## Glycolysis

A basic model of glycolytic oscillations. This is a port of the
[BRAINCIRC implementation](http://www.medphys.ucl.ac.uk/braincirc/download/repos/glyco_oscillations.tar),
which was in turn based on an example from [Keener 1998][9].

* glyco.modeldef

  [9]: http://www.amazon.co.uk/Mathematical-Physiology-Interdisciplinary-Applied-Mathematics/dp/0387983813/
       "Keener J & Sneyd J (1998). Mathematical Physiology. Springer."

## Hodgkin-Huxley

The classic [Hodgkin-Huxley model](https://en.wikipedia.org/wiki/Hodgkin–Huxley_model) of the axonal action potential.

* `huxley.modeldef`

Two simple input files are included:

* `huxley.input`: simulates a single current injection.
* `huxley_multi.input`: simulates a sequence of escalating current injections.

## IP3

A model of IP3 receptor kinetics. This is a port of the
[BRAINCIRC implementation](http://www.medphys.ucl.ac.uk/braincirc/download/repos/IP3Receptor.tar),
which was in turn based on an example from [Keener 1998][9].

* `ip3.modeldef`

Two simple input files are included:

* `ip3.input`: simulates a single interval with no changes.
* `ip3-2.input`: simulates a sequence of time steps with gradually increasing IP3 concentration.

## Kashif

A drastically-simplified adaptation of the Ursino-Lodi cranial blood flow
model from [Ursino 1997][10]. This model was originally presented
in [Kashif 2008][11] and later elaborated in [Kashif 2012][12]. This BCMD implementation
was based on the earlier paper.

* `kashif.modeldef`

The input is is simple sequence of blood flow steps.

* `kashif.input`

 [10]: http://jap.physiology.org/content/82/4/1256.long
       "Ursino M & Lodi CA (1997). Journal of Applied Physiology, 82(4), 1256–1269."
 [11]: http://ieeexplore.ieee.org/xpl/articleDetails.jsp?arnumber=4749055
       "Kashif FM et al (2008). Computers in Cardiology, 35, 369–372."
 [12]: http://dx.doi.org/10.1126/scitranslmed.3003249
       "Kashif FM et al (2012). Science Translational Medicine, 4(129), 129ra44"

## Lorenz

A version of the famous [Lorenz system](https://en.wikipedia.org/wiki/Lorenz_system), an
approximate model of atmospheric convention that can give rise to chaotic behaviour.

* `lorenz.modeldef`

The corresponding input is a trivial one-step simulation.

* `lorenz.input`

## Pendulum

A model of the motion of a pendulum expressed as an index-1 differential-algebraic equation.
Adapted from an [APMonitor example](http://apmonitor.com/wiki/index.php/Apps/PendulumMotion).

* `pendulum.modeldef`

The input file specifies a series of step increases of the pendulum length, *s*.

* `pendulum.input`

## Electrical Circuits

Models of three basic electrical circuits.

* `rc.modeldef`: a circuit containing a single resistor and capacitor.
* `rcr.modeldef`: a circuit with two resistors and one capacitor.
* `lrc.modeldef`: a circuit with an inductor in addition to a resistor and capacitor.

Each circuit has a corresponding simple voltage step sequence input. In addition, there is another
such input for the RC circuit, which is intended to be used for a simple optimisation example.

* `rc.input`
* `rc_target.input`
* `rcr.input`
* `lrc.input`


## HIV

Port of model of HIV infection constructed by Tharindi Hapuarachchi as part of a student project.

* `tharindi.modeldef`

The corresponding input is extremely minimal and merely runs the model with no parameter changes for 6000 s.

* `tharindi.input`

## Two-Pool Calcium Dynamics

A basic two-pool model of calcium-induced calcium release. This is a port of the
[BRAINCIRC implementation](http://www.medphys.ucl.ac.uk/braincirc/download/repos/two_pool_calcium.tar),
which was (yet again) based on an example from [Keener 1998][9].

* `twopool.modeldef`

The input file simulates a gradual increase in cytoplasmic calcium concentration.

* `twopool.input`

## Ursino-Lodi

An implementation of the "classic" Ursino-Lodi cerebral blood flow model from [Ursino 1998][14].

* `urs.modeldef`

The input file performs a gradual ramp down of arterial pressure, then a ramp back up again.

* `urs.input`

  [14]: http://ajpheart.physiology.org/content/274/5/H1715.long
        "Ursino M & Lodi CA (1998). American Journal of Physiology - Heart and Circulatory Physiology, 274(5 Pt 2), H1715–28."

## Windkessel

Three Windkessel blood flow models with increasing numbers of elements. The 2-element and
3-element versions are expressed in electical terms (voltage, current) rather than
hydrodynamic (pressure, flow), but the difference is cosmetic. The 4-element version
is adapted from [Kind 2010][15]

* `wk2.modeldef`
* `wk3.modeldef`
* `wk4.modeldef`

The corresponding input files all describe essentially the same simple sequence of flow
changes through the model.

* `wk2.input`
* `wk3.input`
* `wk4.input`

  [15]: http://doi.org/10.1109/TBME.2010.2041351
        "Kind T et al (2010). IEEE Transactions on Biomedical Engineering, 57(7), 1531–1538."

