from convert import Converter, Variable
import xarray as xr
import fsspec
import json
import sys

kfile = f'/gws/nopw/j04/esacci_portal/kerchunk/kfiles/esacci{sys.argv[-1]}.json'
#kfile = 'kfiles/esacci_lst/esacci_lst_100_b64.json'
outstore = 'kstore/'
refs = Converter(kfile, outstore).load(cache=True, verify=True)

f = open('example_ref.json','w')
f.write(json.dumps(refs))
f.close()

#mapper = fsspec.get_mapper("reference://", fo=refs, target_options={"compression": None})
#ds = xr.open_zarr(mapper)


