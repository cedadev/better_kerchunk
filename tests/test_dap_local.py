import xarray as xr
import fsspec
import matplotlib.pyplot as plt

file_uri = "https://dap.ceda.ac.uk/neodc/esacci/snow/docs/esacci_snow_swe_v2_5.json"
mapper = fsspec.get_mapper("reference://", fo=file_uri)
ds = xr.open_zarr(mapper)

ds.swe.mean(dim='time').plot()
plt.show()
plt.savefig('snow5_dap.png')
