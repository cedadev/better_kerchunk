'''
KFG - Kerchunk-Fileset Generators

Initial Plan: (KFG converter)
 - Obtain kerchunk refs json object from existing kerchunk file
 - Perform install_generators new routine per variable
 - Write meta data file
 - Write each netcdf file for each variable bundle
'''

from kerchunk.hdf import SingleHdf5ToZarr
from kerchunk.combine import MultiZarrToZarr
from kerchunk.utils import consolidate

import base64
import json
import jinja2
import numpy as np
from scipy import stats

from datetime import datetime

def open_kerchunk_json():
    tdict = {}
    return tdict

def access_reference(freference, time_dim=1):
    """
    Collect variables from netcdf reference file
    Determine chunking dimensions (if chunking() == 2, assume lat/lon)
    """
    from netCDF4 import Dataset
    print('[INFO] Accessing Reference')

    # These dimensions are always ignored when retrieving variables
    ignore = ['lat','lon','latitude','longitude','time']
    reference = Dataset(freference)
    maxdims = 0
    checkvars = {}

    # Determine which variables are chunked with which structure.
    for var in reference.variables.keys():
        if var not in ignore:
            dims = reference.variables[var].chunking()
            
            # Determine number of chunked dims per variable
            if dims != 'contiguous':
                ndims = 0
                for dim in dims:
                    if int(dim) > 1:
                        ndims += 1
                key = ndims
                if maxdims < ndims:
                    maxdims = ndims
            else:
                key = dims

            # Collect variables in dict by number of chunked dims.
            if key in checkvars:
                checkvars[key].append(var)
            else:
                checkvars[key] = [var]

    # Check for no internal chunking
    if maxdims == 0:
        variables = checkvars['contiguous']
    else:
        variables = False
        # Find highest number of chunks and collect variables
        while maxdims > 1 and not variables:
            if maxdims in checkvars:
                variables = checkvars[maxdims]
                keepdims = maxdims
            maxdims -= 1
    dims = reference.variables[variables[0]].dimensions

    ndims = []
    chunks = reference.variables[variables[0]].chunking()
    for i, dim in enumerate(dims):
        if i == 0:
            ndims.append(time_dim)
        else:
            # Determine number of chunks from size of total dimension and size of each chunk
            if chunks != 'contiguous':
                ndims.append(int( int(reference.dimensions[dim].size) / int(chunks[i]) ))
            else:
                ndims.append(1)
    return variables, ndims

def install_generators(out, variables, dims):
    """
    Pack chunk arrays into custom generators.

    Single chunk reference pass followed by analysis of lengths and offsets
    Use of numpy arrays rather than python lists to improve performance.
    """
    
    def update(countdim, dims, index):
        countdim[index] += 1
        if countdim[index] >= dims[index]:
            countdim[index] = 0
            countdim = update(countdim, dims, index-1)
        return countdim

    refs = out['refs']
    
    countdim = [0 for dim in dims]
    countdim[-1] = -1
    maxdims = [dim-1 for dim in dims]
    chunkindex = 0
    files, skipchunks = [], {}
    filepointer = 0
    ## Stage 1 pass ##
    # - collect skipchunks
    # - collect files
    # - collect offsets and lengths for determining lengths

    print('[INFO] Installing Generator')
    lengths, offsets = [],[]
    while countdim != maxdims:
        countdim = update(countdim, dims, -1)
        # Iterate over dimensions and variables, checking each reference in turn
        for vindex, var in enumerate(variables):
            key = var + '/' + '.'.join(str(cd) for cd in countdim)
            # Compile Skipchunks
            if key not in refs:
                try:
                    skipchunks['.'.join(str(cd) for cd in countdim)][vindex] = 1
                except:
                    skipchunks['.'.join(str(cd) for cd in countdim)] = [0 for v in variables]
                    skipchunks['.'.join(str(cd) for cd in countdim)][vindex] = 1
                try:
                    offsets.append(offsets[-1] + lengths[-1])
                except:
                    offsets.append(0)
                lengths.append(0)
            else:
                # Compile offsets and lengths
                lengths.append(refs[key][2])
                offsets.append(refs[key][1])
                
                # Determine files collection
                filename = refs[key][0]
                if len(files) == 0:
                    files.append([-1, filename])
                if filename != files[filepointer][1]:
                    files[filepointer][0] = chunkindex-1
                    filepointer += 1
                    files.append([chunkindex, filename])
                del out['refs'][key]
            chunkindex += 1
    # Set final file chunk index
    files[-1][0] = chunkindex
    
    lengths = np.array(lengths, dtype=int)
    offsets = np.array(offsets, dtype=int)

    nzlengths = lengths[lengths!=0]
    # Find standard lengths
    slengths = [
        int(stats.mode(
            nzlengths[v::len(variables)]
        )[0]) 
        for v in range(len(variables)) ] # Calculate standard chunk sizes

    # Currently have files, variables, varwise, skipchunks, dims, start, lengths, dimensions
    # Still need to construct unique, gaps

    lv = len(variables)
    uniquelengths, uniqueids = np.array([]), np.array([])
    positions = np.arange(0, len(lengths), 1, dtype=int)
    additions = np.roll((offsets + lengths), 1)
    additions[0] = offsets[0] # Reset initial position

    gaplengths = (offsets - additions)[(offsets - additions) != 0]
    gapids     = positions[(offsets - additions) != 0]

    for v in range(lv):
        q = lengths[v::lv][lengths[v::lv] != slengths[v]]
        p = positions[v::lv][lengths[v::lv] != slengths[v]]
        p = p[q!=0]
        q = q[q!=0]
        uniquelengths = np.concatenate((
            uniquelengths,
            q
        ))
        uniqueids = np.concatenate((
            uniqueids,
            p
        ))
        gapmask    = np.abs(gaplengths) != slengths[v]
        gaplengths = gaplengths[gapmask]
        gapids     = gapids[gapmask]
    
    # Uniques must be in order.
    sortind = np.argsort(uniqueids)
    uniqueids = uniqueids[sortind]
    uniquelengths = uniquelengths[sortind]

    out['gen'] = {
        "files": files,
        "variables" : list(variables),
        "varwise" : True,
        "skipchunks" : skipchunks,
        "dims" : dims,
        "unique": {
            "ids": [int(id) for id in uniqueids],
            "lengths": [int(length) for length in uniquelengths],
        },
        "gaps": {
            "ids": [int(id) for id in gapids],
            "lengths": [int(length) for length in gaplengths],
        },
        "start": str(offsets[0]),
        "lengths": list(slengths),
        "dimensions" : {
            "i":{
                "stop": str(chunkindex)
            }
        },
        "gfactor": str( 1 - (len(skipchunks) + len(uniqueids) + len(gapids))/chunkindex)[:4],
    }
    print('[INFO] Installed Generator')

    return out

def get_coords(count, dims):  
    """
    Assemble key variable-wise rather than chunk-wise.

    Convert count index to dimension coordinates for this chunk structure
    """
    products = []
    for index in range(len(dims)):
        p = 1
        for prod in dims[index+1:]:
            p = p * int(prod)
        products.append(p)

    key = []
    for x,p in enumerate(products):
        key.append(str(int(count//p)))
        count -= p*(count//p)

    return '.'.join(key)


def fast_write_files_keys(files, vars, dims, refnum):
    tot = 0
    fcount = 0
    nfiles, keys = [],[]
    for ref in range(int(refnum/len(vars))):
        t0 = datetime.now()
        coords = get_coords(ref, dims)
        tot += (datetime.now()-t0).total_seconds()
        if ref > files[fcount][0]:
            fcount += 1
        for v in vars:
            nfiles.append(files[fcount][1])
            keys.append(f'{vars}/{coords}')
    return nfiles, keys

def fast_unpack(out):
    print('[INFO] Unpacking Generator')
    refnum = int(out['gen']['dimensions']['i']['stop'])
    refs_per_var = int(refnum/len(out['gen']['lengths']))
    gaps = np.zeros((refnum,))
    sizes = np.zeros((0,))
    for vindex in range(len(out['gen']['lengths'])):

        vsizes = np.zeros((refs_per_var,))
        vsizes[:] = out['gen']['lengths'][vindex]
        sizes = np.concatenate((sizes, vsizes))

    uniqueids     = np.array(out['gen']['unique']['ids'])
    uniquelengths = np.array(out['gen']['unique']['lengths'])

    gapids        = np.array(out['gen']['gaps']['ids'])
    gaplengths    = np.array(out['gen']['gaps']['lengths'])

    gaps[gapids] = gaplengths

    sizes[uniqueids] = uniquelengths
    cs_sizes = np.cumsum(sizes)
    gs_sizes = np.cumsum(gaps)
    offsets = cs_sizes + gs_sizes
    offsets = np.roll(offsets, 1)
    offsets[0] = 0
    offsets += int(out['gen']['start'])
    
    base = np.transpose([offsets, sizes])

    newsize = len(sizes)
    pairs = np.reshape(base, (newsize, 2))
    files = out['gen']['files']
    vars = out['gen']['variables']
    dims = out['gen']['dims']

    crange = (newsize-1000, newsize-900)


    nfiles, keys = fast_write_files_keys(files, vars, dims, crange)
    
    tdict = {}
    for x in range(crange):
        tdict[keys[x]] = [nfiles[x], pairs[x][0], pairs[x][1]]
    

    print('[INFO] Generator Unpacked')
    return None

def main():
    # Open kerchunk file as out
    # Access reference with freference file
    test_kerchunk = 'kc-indexes/ESA/e1000_og.json'
    rfile = "/neodc/esacci/land_surface_temperature/data/AQUA_MODIS/L3C/0.01/v3.00/daily/2002/07/04/ESACCI-LST-L3C-LST-MODISA-0.01deg_1DAILY_NIGHT-20020704000000-fv3.00.nc"
    t0 = datetime.now()
    print('[INFO] Starting process')
    f = open(test_kerchunk,'r')
    out = json.load(f)
    f.close()
    print(f'[INFO] Opened kerchunk file - {(datetime.now()-t0).total_seconds()}s')
    tnow = datetime.now()

    variables, ndims = access_reference(rfile, time_dim=1000)
    print(f'[INFO] Accessed Reference - {(datetime.now()-tnow).total_seconds()}s')
    tnow = datetime.now()
    out = install_generators(out, variables, ndims)
    print(f'[INFO] Installed Generators - {(datetime.now()-tnow).total_seconds()}s')
    tnow = datetime.now()
    fast_unpack(out)
    print(f'[INFO] Unpacked Generators - {(datetime.now()-tnow).total_seconds()}s')
    if False:
        f = open('kc-indexes/testgen.json','w')
        f.write(json.dumps(out))
        f.close()
    print('Success')
    
main()