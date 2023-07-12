from convert import Converter, Variable

kfile = 'esacci_snow_swe_v2_5_b64.json'
outstore = './'
Converter(kfile, outstore).process()

