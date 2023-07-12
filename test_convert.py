from convert import Converter, Variable

kfile = 'kfiles/esacci_snow_swe_v2_5_b64.json'
outstore = 'kstore/'
Converter(kfile, outstore).process()

