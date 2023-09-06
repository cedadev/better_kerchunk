from unpack import get_mapper
import xarray as xr

file = 'kc-indexes/ESA/e1000_gen.json'

mapper = get_mapper("reference://", fo=file, target_options={"compression": None})
ds = xr.open_zarr(mapper)

print(ds)