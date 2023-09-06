from convert import Converter, Variable
import sys

#kfile = 'kfiles/esacci_snow_swe_v2_5_b64.json'
kfile = f'/gws/nopw/j04/esacci_portal/kerchunk/kfiles/esacci{sys.argv[-1]}.json'
outstore = 'kstore/'
Converter(kfile, outstore).process()

