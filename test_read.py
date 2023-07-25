from convert import Converter, Variable
import xarray as xr
import fsspec
import json

kfile = 'kfiles/esacci_snow_swe/esacci_snow_swe_v2_5_b64.json'
#kfile = 'kfiles/esacci_lst/esacci_lst_100_b64.json'
outstore = 'kstore/'
refs = Converter(kfile, outstore).load(cache=True, verify=True)

#mapper = fsspec.get_mapper("reference://", fo=refs, target_options={"compression": None})
#ds = xr.open_zarr(mapper)


