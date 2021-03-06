import os
from numpy import allclose
import astropy.units as u

curdir = os.path.dirname(__file__)
datadir = os.path.join(curdir, 'data')


def load_transmission(infile=None, **kwargs):
    """

    Parameters
    ----------

    infile
        The full path to the input transmission file


    Loads the glass transmission. For now, does a little math on this
    top account for the multiple pieces of glass with different widths.


    Returns
    -------
    wave : 1D array
        Wavelength values from the input file, with Astropy units

    transmisison : 1D array
        transmission values, normalized to 1

    Example
    -------

    >>> from astroduet.config import Telescope
    >>> duet = Telescope()
    >>> wave, transmission = load_transmission(duet.transmission_file)
    >>> allclose(transmission[120], 0.8794079028314423)
    True


    """
    assert infile is not None, 'load_transmission: Provide an input transmission file'

    from numpy import genfromtxt

    data = genfromtxt(infile, skip_header=2, delimiter=',')
    wave = data[:,0]*u.nm
    thin = data[:,1] / 100.
    thick = data[:, 6] / 100.

    # Right now this is a 3mm and two 10 mm thick pieces of glass
    transmission = thin * thick * thick

    return wave, transmission


def load_qe(infile = None, **kwargs):
    """

    Parameters
    ----------

    infile
        The full path to the input QE file


    Loads the detector QE and returns the values.

    Returns
    -------
    wave : 1D array
        Wavelength values from teh input file, with Astropy units

    qe : 1D array
        QE values, normalized to 1

    Example
    -------

    >>> from astroduet.config import Telescope
    >>> duet = Telescope()
    >>> band = 1
    >>> wave, qe = load_qe(infile=duet.qe_files['names'][band])
    >>> allclose(qe[120], 0.841579)
    True

    """
    import numpy as np

    band = kwargs.pop('band', 1)
    diag = kwargs.pop('diag', False)

    assert infile is not None, 'load_qe: Provide an input QE file'

    data = np.genfromtxt(infile, skip_header=2, delimiter=',')


    wave = data[:,0]*u.nm
    qe = data[:,3] / 100.




    return wave, qe

def load_reflectivity(infile = None, **kwargs):
    """
    Loads the optics reflectivity and returns the values.

    Parameters
    ----------

    infile
        The full path to the input reflectivity file


    Loads the primary mirror reflectivity and returns the values.

    Returns
    -------
    wave : 1D array
        Wavelength values from teh input file, with Astropy units

    reflectivity : 1D array
        Reflectivity values, normalized to 1

    Example
    -------

    >>> from astroduet.config import Telescope
    >>> duet = Telescope()
    >>> wave, reflectivity = load_reflectivity(infile=duet.reflectivity_file['name'])
    >>> allclose(reflectivity[50], 0.895383)
    True

    """
    import astropy.units as ur
    import numpy as np

    diag = kwargs.pop('diag', False)

    assert infile is not None, 'load_reflectivity: Need an input file'


#    infile = os.path.join(datadir, 'al_mgf2_mirror_coatings.csv')

    f = open(infile, 'r')
    header = True
    qe = {}
    set = False
    for line in f:
        if header:
            header = False
            continue
        fields = line.split(',')
        if not set:
            wave = float(fields[0])
            reflectivity = float(fields[1])
            set = True
        else:
            wave = np.append(wave, float(fields[0]))
            reflectivity = np.append(reflectivity, float(fields[1]))

    f.close()

    # Give wavelength a unit
    wave *= ur.nm

    if diag:
        print('Optics reflectivity loader')
        print('Input file {}'.format(infile))


    return wave, reflectivity/100.

def load_redfilter(infile = None, shift_by=None, **kwargs):
    """
    Loads the bandpass filter and returns the transmission values.

    Parameters
    ----------

    infile : str, default None
        The full path to the input bandpass file

    Other parameters
    ----------------
    shift_by : `astropy.quantity.Quantity`
        Shift redfilter wavelength by this amount. Good for experiments.

    Returns
    -------
    wave : 1D array
        Wavelength values from the input file, with Astropy units

    reflectivity : 1D array
        Reflectivity values, normalized to 1

    Example
    -------

    >>> from astroduet.config import Telescope
    >>> duet = Telescope()
    >>> wave, redfilter = \\
    ...    load_redfilter(infile=duet.bandpass_files['names'][0])
    >>> allclose(redfilter[70], 0.21605899999999997)
    True
    >>> allclose(wave[0].value, 150.)
    True
    >>> wave, redfilter = \\
    ...    load_redfilter(infile=duet.bandpass_files['names'][0],
    ...                   shift_by=10 * u.nm)
    >>> allclose(redfilter[70], 0.21605899999999997)
    True
    >>> allclose(wave[0].value, 160.)
    True

    """
    import astropy.units as ur
    import numpy as np

    band = kwargs.pop('band', 1)
    diag = kwargs.pop('diag', False)
    light = kwargs.pop('light', True)
    filter_type = kwargs.pop('filter_type', 'B')

    available = ['A', 'B', 'C']
    cols = [3, 7, 11]

    assert filter_type in available, \
        'load_redfilter: Provide a valid filter type'
    trans_col = cols[available.index(filter_type)]

    assert infile is not None, 'load_redfilter: Need an input file'
    data = np.genfromtxt(infile, skip_header=4, delimiter=',')
    wave = data[:,0]*u.nm

    if shift_by is not None:
        wave += shift_by

    transmission = data[:, trans_col] / 100.

    return wave, transmission


def apply_trans(wav_s, flux_s, wav_t, trans, **kwargs):
    """
    Interpolates transmission curve onto source wavelength array, applies transmission curve.

    Required inputs:
    wav_s (wavelength array of source spectrum, numpy array with units)
    flux_s (source spectrum, numpy array with units)
    wav_t (wavelength array of transmission curve, numpy array with units)
    trans (transmission curve, numpy array without units)

    Optional Inputs (defaults):
    diag = Diagnostics toggle (False)

    Returns corrected input spectrum

    """

    import astropy.units as ur
    import astropy.constants as cr
    import numpy as np

    # Check if the inputs make sense
    assert len(wav_s) == len(flux_s), "Input spectrum and corresponding wavelength array are not the same length"
    assert len(wav_s) == len(flux_s), "Input spectrum and corresponding wavelength array are not the same length"
    assert len(wav_t) == len(trans), "Transmission curve and corresponding wavelength array are not the same length"
    assert max(trans) <= 1., "Values larger than 1 found in transmission curve"
    assert min(trans) >= 0., "Values smaller than 0 found in transmission curve"
    assert wav_s.unit.is_equivalent(ur.m), "Input wavelength array does not have unit of length"
    assert wav_t.unit.is_equivalent(ur.m), "Transmission wavelength array does not have unit of length"

    # Make sure wav_s and wav_t are in the same units for interpolation
    wav_ttrue = wav_t.to(wav_s.unit)

    # Interpolate transmission curve onto source wavelength array
    trans_int = np.interp(wav_s,wav_ttrue,trans)

    # Correct input spectrum:
    flux_corr = flux_s * trans_int

    diag = kwargs.pop('diag', False)

    if diag:
        print('Diagnostics?')

    return flux_corr

def filter_parameters(duet=None, *args, **kwargs):
    """
    Construct the effective central wavelength and the effective bandpass
    for the filters.

    Parameters
    ----------


    Other parameters
    ----------------
    vega : conditional, default False
        Use the Vega spetrum (9.8e3 K blackbody) to compute values. Otherwise computed
        "flat" values if quoting AB mags.

    diag : conditional, default False
        Show the diagnostic info on the parameters.

    Examples
    --------
    >>> band1, band2 = filter_parameters()
    >>> allclose(band1['eff_wave'].value, 198.63858525)
    True

    """
    from astroduet.config import Telescope

    if duet is None:
        duet = Telescope()

    from astropy.modeling import models
    from astropy.modeling.blackbody import FNU, FLAM
    from astropy import units as u
    import numpy as np

    vega = kwargs.pop('vega', False)
    diag = kwargs.pop('diag', False)

    wave = np.arange(1000, 10000)*u.AA
    if vega:
        temp = 9.8e3*u.K
        bb = models.BlackBody1D(temperature=temp)
        flux = bb(wave).to(FLAM, u.spectral_density(wave))
    else:
        flat_model =  np.zeros_like(wave.value)
        flat_model += 1
        flat_model *= FNU
        flux = flat_model.to(FLAM, u.spectral_density(wave))



    band1 = duet.apply_filters(wave, flux, band=1, **kwargs)
    band2 = duet.apply_filters(wave, flux, band=2, **kwargs)


    λ_eff1 = ((band1*wave).sum() / (band1.sum())).to(u.nm)
    λ_eff2 = ((band2*wave).sum() / (band2.sum())).to(u.nm)

    dλ = wave[1] - wave[0]
    t1 = band1 / flux
    t2 = band2 / flux

    w1 = (dλ * t1.sum() / t1.max()).to(u.nm)
    w2 = (dλ * t2.sum() / t2.max()).to(u.nm)

    band1 = {'eff_wave': λ_eff1,
             'eff_width': w1}
    band2 = {'eff_wave': λ_eff2,
             'eff_width': w2}

    if diag:
        print('Band1: {0:0.2f} λ_eff, {1:0.2f} W_eff'.format(λ_eff1, w1))
        print('Band2: {0:0.2f} λ_eff, {1:0.2f} W_eff'.format(λ_eff2, w2))

    return band1, band2
















