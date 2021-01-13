import astropy.table as atpy
import httpio
import numpy as np
import astropy.io.fits as pyfits
import urllib3
import os
from pylru import lrudecorator
urllib3.disable_warnings()


class si:
    DESI_USER = None
    DESI_PASSWD = None


def get_desi_login_password():
    if si.DESI_USER is None:
        config = os.environ['HOME'] + '/.desi_http_user'
        if not os.path.exists(config):
            raise Exception('''You need to specify the DESI_USER/DESI_PASSWD.
put them in $HOME/.desi_http_user like that
username:password
''')
        user, pwd = open(config).read().rstrip().split(':')
        si.DESI_USER, si.DESI_PASSWD = user, pwd
    return si.DESI_USER, si.DESI_PASSWD


@lrudecorator(100)
def get_specs(tileid=None,
              night=None,
              fiber=None,
              targetid=None,
              expid=None,
              coadd=False,
              dataset='andes',
              mask=False,
              ivar=False):
    """
    Get DESI spectra 
    
    Parameters
    ----------
    tileid: int
    night: int
    fiber: int
    targetid: int
    expid: int (optional)
    coadd: bool 
         If true read coadded spectra

    Returns
    -------
    ret: list(dict)
        The list of dictionaries where each dictionary
        has keywords b_wavelength, r_wavelength, z_wavelength
        b_flux etc

    """
    if coadd:
        prefix = 'coadd'
    else:
        prefix = 'spectra'
    spectrograph = fiber // 500
    url = f'https://data.desi.lbl.gov/desi/spectro/redux/{dataset}/tiles/{tileid}/{night}/{prefix}-{spectrograph}-{tileid}-{night}.fits'
    user, pwd = get_desi_login_password()
    kw = dict(auth=(user, pwd), verify=False)

    with httpio.open(url, **kw) as fp:
        hdus = pyfits.open(fp)
        ftab = atpy.Table(hdus['FIBERMAP'].data)

        if expid is not None:
            xind = ftab['EXPID'] == expid
        else:
            xind = np.ones(len(ftab), dtype=bool)
        if targetid is not None:
            xids = np.nonzero((ftab['TARGETID'] == targetid) & xind)[0]
        else:
            xids = np.nonzero((ftab['FIBER'] == fiber) & xind)[0]
        if len(xids) == 0:
            print('no spectra')
            return []

        waves = {}
        for arm in 'BRZ':
            waves[arm] = hdus[arm + '_WAVELENGTH'].data

        fluxes = {}
        for arm in 'BRZ':
            fluxes[arm] = hdus[arm + '_FLUX'].section

        masks = {}
        if mask:
            for arm in 'BRZ':
                masks[arm] = hdus[arm + '_MASK'].section

        ivars = {}
        if ivar:
            for arm in 'BRZ':
                ivars[arm] = hdus[arm + '_IVAR'].section

        rets = []
        for xid in xids:
            ret = dict(b_wavelength=waves['B'],
                       r_wavelength=waves['R'],
                       z_wavelength=waves['Z'])
            for arm in 'BRZ':
                ret[arm.lower() + '_flux'] = fluxes[arm][xid, :]
            if mask:
                for arm in 'BRZ':
                    ret[arm.lower() + '_mask'] = masks[arm][xid, :]
            if ivar:
                for arm in 'BRZ':
                    ret[arm.lower() + '_ivar'] = ivars[arm][xid, :]

            rets.append(ret)
        return rets


@lrudecorator(100)
def get_rvspec_models(tileid=None,
                      night=None,
                      fiber=None,
                      targetid=None,
                      expid=None,
                      coadd=False,
                      run='200507',
                      dataset='andes'):
    """
    Get RVSpecfit models
    
    Parameters
    ----------
    tileid: int
    night: int
    fiber: int
    targetid: int
    expid: int (optional)
    coadd: bool
         If true read coadded spectra
    run: string
         The string identifying a software run
    dataset: the dataset fitted (i.e. andes/sv_daily)

    Returns
    -------
    ret: list(dict)
        The list of dictionaries where each dictionary
        has keywords b_wavelength, r_wavelength, z_wavelength
        b_model etc
    """

    if coadd:
        prefix = 'rvmod_coadd'
    else:
        prefix = 'rvmod_spectra'
    spectrograph = fiber // 500
    url = f'https://data.desi.lbl.gov/desi/science/mws/redux/{dataset}/rv_output/{run}/{tileid}/{night}/{prefix}-{spectrograph}-{tileid}-{night}.fits'
    user, pwd = get_desi_login_password()
    kw = dict(auth=(user, pwd), verify=False)
    with httpio.open(url, **kw) as fp:
        hdus = pyfits.open(fp)
        ftab = atpy.Table(hdus['FIBERMAP'].data)

        if expid is not None:
            xind = ftab['EXPID'] == expid
        else:
            xind = np.ones(len(ftab), dtype=bool)
        if targetid is not None:
            xids = np.nonzero((ftab['TARGETID'] == targetid) & xind)[0]
        else:
            xids = np.nonzero((ftab['FIBER'] == fiber) & xind)[0]

        if len(xids) == 0:
            print('no spectra')
            return []
        bwave = hdus['B_WAVELENGTH'].data
        rwave = hdus['R_WAVELENGTH'].data
        zwave = hdus['Z_WAVELENGTH'].data

        rets = []
        bdata = hdus['B_MODEL'].section
        rdata = hdus['R_MODEL'].section
        zdata = hdus['Z_MODEL'].section
        rets = []
        for xid in xids:
            bdata_cur = bdata[xid, :]
            rdata_cur = rdata[xid, :]
            zdata_cur = zdata[xid, :]

            ret = dict(b_wavelength=bwave,
                       r_wavelength=rwave,
                       z_wavelength=zwave,
                       b_model=bdata_cur,
                       r_model=rdata_cur,
                       z_model=zdata_cur)
            rets.append(ret)
        return rets
