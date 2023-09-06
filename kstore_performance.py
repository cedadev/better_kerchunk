# Standard Imports
import fsspec
import xarray as xr
import matplotlib.pyplot as plt
import sys
import math
import numpy as np
import ssl
from datetime import datetime
from convert import Converter, Variable

# Utilities
def find_variable(ds, display=False):
    keepvar = None
    for var in ds.variables:
        if display:
            print(var, len(ds[var].dims))
        if not keepvar and len(ds[var].dims) == 3:
            k = True
            for l in ['lat','lon','time']:
                k = k and l in ds[var].dims
            if k:
                keepvar = var
    if keepvar == None:
        if not display: # Built-in single recursion in the case of failure to find a correct variable
            find_variable(ds, display=True)
        else:
            return None
    return keepvar

def getbox(map_bounds, latn, lonn):
    latmin = int((map_bounds[2]+90)/180 * latn)
    latmax = int((map_bounds[0]+90)/180 * latn)
    
    lonmin = int((map_bounds[3]+180)/360 * lonn)
    lonmax = int((map_bounds[1]+180)/360 * lonn)
    return [latmin, latmax, lonmin, lonmax]

kfile = '/gws/nopw/j04/esacci_portal/kerchunk/kfiles/esacci12.json'

outstore = 'kstore/'
refs = Converter(kfile, outstore).load(verify=True)
import json
with open('extracted.json','w') as f:
    f.write(json.dumps(refs))

print('Starting Untimed ref check section')
mapper = fsspec.get_mapper('reference://', fo='extracted.json')
ds     = xr.open_zarr(mapper, consolidated=False)

latn  = len(ds.lat)
lonn  = len(ds.lon)
timen = len(ds.time)
ref = 1e6

# Determine the standard byte density
# To ensure the plotted box does not exceed the reference value in memory
map_bounds = [1,1,0,0]
[latmin, latmax, lonmin, lonmax] = getbox(map_bounds, latn, lonn)
mbytes      = (latmax-latmin)*(lonmax-lonmin)*64
sf          = math.sqrt(ref/mbytes)
if sf < 75:
    bounds = [
        map_bounds[0] + (sf-1)/2,
        map_bounds[1] + (sf-1)/2,
        map_bounds[2] - (sf-1)/2,
        map_bounds[3] - (sf-1)/2
    ]
    [latmin, latmax, lonmin, lonmax] = getbox(bounds, latn, lonn)
    if latmin == latmax or lonmin == lonmax:
        print('Bound Box too small, try a larger size')
        sys.exit()
    mbytes = (latmax-latmin)*(lonmax-lonmin)*64
else:
    bounds = [90, 180, -90, -180]
    latmin = 0
    latmax = latn
    lonmin = 0
    lonmax = lonn
    mbytes = (latmax-latmin)*(lonmax-lonmin)*64

map_bounds = bounds
var = find_variable(ds)
sections = []
broken = False
i = 0
while not broken and i < timen:
    sect = ds[var][i,latmin:latmax,lonmin:lonmax]
    if np.count_nonzero(np.isnan(sect)) < (latmax-latmin)*(lonmax-lonmin):
        # Valid non-empty
        if len(sections) > 0:
            if sections[len(sections)-1] != i-1:
                broken = True
            else:
                sections.append(i)
        else:
            sections.append(i)
    else:
        # Invalid
        if len(sections) > 0:
            broken = True

    if len(sections) > 5:
        broken = True # Look at 5 timesteps
    print(f'{i} / {timen}')
    i += 1
if len(sections) < 1:
    print('No valid timesteps found - exiting')
    sys.exit()
timeslice = [sections[0], sections[-1]]
if timeslice[0] == timeslice[1]:
    timeslice[1] += 1
mbytes = mbytes*(timeslice[1]-timeslice[0])

print(var, map_bounds, timeslice)
print('Expected MSize:',mbytes)

## Dap Test
print('Starting Dap Test')
t1 = datetime.now()
refs = Converter(kfile, outstore).load()
mapper = fsspec.get_mapper('reference://', fo=refs, target_options={'compression':None})
dap    = xr.open_zarr(mapper, consolidated=False, decode_times=False)
da     = dap[var]
region = da[timeslice[0]:timeslice[1],latmin:latmax,lonmin:lonmax].mean(dim='time') #da.sel(lat=slice(map_bounds[2], map_bounds[0]), lon=slice(map_bounds[3], map_bounds[1]))
region.plot()
plt.savefig(f'reg{ord}_dap.png')
print((datetime.now()-t1).total_seconds())
