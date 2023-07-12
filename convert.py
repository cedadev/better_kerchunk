# Convert.py

# Take existing kerchunk json (standard file)
#  - ideally with lat/lon as b64 encoded but not hugely important

# Create kerchunk_store from json file
#  - meta.json with only the metadata
#  - var.nc for each variable

import json
import numpy as np

from netCDF4 import Dataset

class Variable:
    def __init__(self, var):
        self.var = var
        self.files = []
        self.sizes = []
        self.offsets = []
        self.keys = []

    def update(key, segments):
        # Update arrays with new attributes
        self.keys.append(key)
        self.files.append(segments[0])
        self.sizes.append(segments[1])
        self.offsets.append(segments[2])

class Converter:
    def __init__(self,kfile, outpath):
        self.kfile = kfile
        self.store = os.path.join(outpath, kfile.split('/')[-1].replace('.json',''))
        self.metadata = {}

    def deconstruct(refs):

        # Setup metadata dict
        keywords = ['lat','lon','.zarray','zgroup','.zattrs']
        for key in refs.keys():
            if key == 'refs':
                self.metadata[key] = {}
            else:
                self.metadata[key] = refs[key]
        
        # Setup vars dict
        self.vars = {}
        for key in refs['refs'].keys():
            try:
                firstpart, secondpart = key.split('/')
                if firstpart in keywords or secondpart[0] == '.':
                    self.metadata['refs'][key] = refs['refs'][key]
                else:
                    variable = firstpart
                    if variable not in self.vars:
                        self.vars[variable] = Variable(variable)
                    self.vars[variable].update(secondpart, refs['refs'][key])

            except ValueError:
                self.metadata['refs'][key] = refs['refs'][key] 
    
    def make_store():
        if not os.path.isdir(self.store):
            os.makedirs(self.store)

    def write_meta():
        meta = os.path.join(self.store, 'meta.json' )
        if not os.path.isfile(meta):
            os.system(f'touch {meta}')
        f = open(meta, 'w')

    def write_ncs():
        pass

    def process():
        pass
