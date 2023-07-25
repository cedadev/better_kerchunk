# Writing a kerchunk local/dap file
import os
from datetime import datetime
from convert import Converter, Variable

PATH = '/home/users/dwest77/Documents/kerchunk_dev/kerchunk-tools/kerchunk_tools'
fpattern = '/neodc/esacci/land_surface_temperature/data/AQUA_MODIS/L3C/0.01/v3.00/monthly/*/*/*MONTHLY_DAY*.nc'
savename = 'ktest'

os.system(f'ls {fpattern} > {PATH}/filelists/{savename}.txt')

# Basic Kerchunk
t1 = datetime.now()
os.system(f'python {PATH}/cli.py create -f {PATH}/filelists/{savename}.txt -o {savename}.json -b 1')
t2 = datetime.now()

# Kerchunk DAP
os.system(f'sed -i s+/neodc+https://dap.ceda.ac.uk/neodc+g kc-indexes/{savename}.json')
t3 = datetime.now()

# Kerchunk Store
outstore = 'kstore/'
ta = datetime.now()
Converter(f'kc-indexes/{savename}.json', outstore).process()
tb = datetime.now()
ttot = (t2-t1).total_seconds() + (tb-ta).total_seconds()

# Info
print('Kerchunk Local:',(t2-t1).total_seconds(),'s')
print('Kerchunk DAP:',(t3-t1).total_seconds(),'s')
print('Kerchunk Store:',ttot,'s')