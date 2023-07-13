# Convert.py

# Take existing kerchunk json (standard file)
#  - ideally with lat/lon as b64 encoded but not hugely important

# Create kerchunk_store from json file
#  - meta.json with only the metadata
#  - var.nc for each variable

import json
import numpy as np
import os

from netCDF4 import Dataset
from scipy import stats

from json import JSONEncoder

class NumpyArrayEncoder(JSONEncoder):
    def default(self,obj):
        if isinstance(obj,np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self,obj)

class Variable:
    def __init__(self, var, store):
        self.var = var
        self.store = store
        self.files = []
        self.sizes = []
        self.offsets = []
        self.keys = []
        self.fileids = []
        self.fcounter = 0
        self.latestfile = None

    def update(self,key, segments):
        # Update arrays with new attributes
        if segments[0] != self.latestfile:
            self.fileids.append(self.fcounter)
            self.latestfile = segments[0]
        else:
            self.fcounter += 1
        self.keys.append(key)
        self.sizes.append(segments[1])
        self.offsets.append(segments[2])

    def get_entry(self):
        return [self.chunks, self.msize, self.moffset]

    def unpack_gen(self):
        # Assume we've already collected the json/netcdf contents
        # Also assume we have the file arrays and everything
        sizes = np.zeros(self.chunks) + self.msize
        offsets = np.zeros(self.chunks) + self.moffset
        files = np.zeros(self.chunks)
        keys = self.keys
        init = 0
        for x, f in enumerate(self.files):
            files[init:self.fileids[x]] = f
        


    def pack_gen(self):
        self.chunks = len(self.sizes)
        sizes = np.array(self.sizes,dtype=int)
        offsets = np.array(self.offsets,dtype=int)
        
        self.msize = int(stats.mode(sizes).mode)
        self.moffset = int(stats.mode(offsets).mode)

        self.uniquelengths = sizes[sizes != self.msize]
        self.uniqueids = np.arange(0,len(sizes))[sizes != self.msize]

        self.gaplengths = offsets[offsets != self.moffset]
        self.gapids = np.arange(0,len(offsets))[offsets != self.moffset]

        del sizes
        del offsets
        del self.sizes
        del self.offsets


        # Get uniqueids, uniquelengths
        # Get gapids, gaplengths

    def write_nc(self):
        ncfile = f'{self.store}/{self.var}.nc'
        ncf_new = Dataset(ncfile, 'w', format='NETCDF4')

        unique_dim = ncf_new.createDimension('unique_dim',len(self.uniqueids))
        keys_dim = ncf_new.createDimension('keys_dim',len(self.keys))
        gaps_dim = ncf_new.createDimension('gaps_dim',len(self.gapids))

        unique_ids = ncf_new.createVariable('unique_ids', np.int32, ('unique_dim',))
        unique_ids[:] = self.uniqueids
        unique_lens = ncf_new.createVariable('unique_lengths', np.int32, ('unique_dim',))
        unique_lens[:] = self.uniquelengths

        gap_ids = ncf_new.createVariable('gap_ids', np.int32, ('gaps_dim',))
        gap_ids[:] = self.gapids
        gap_lens = ncf_new.createVariable('gap_lengths', np.int32, ('gaps_dim',))
        gap_lens[:] = self.gaplengths

        keys = ncf_new.createVariable('keys', np.str_, ('keys_dim',))
        keys[:] = np.array(self.keys)

    def write_json(self):
        jsfile = f'{self.store}/{self.var}.json'
        refs = {
            'unique_ids':self.uniqueids,
            'unique_lengths':self.uniquelengths,
            'gap_ids':self.gapids,
            'gap_lengths':self.gaplengths,
            'keys':self.keys,
            'fileids':self.fileids,
        }
        f = open(jsfile,'w')
        f.write(json.dumps(refs, cls=NumpyArrayEncoder))
        f.close()



class Converter:
    def __init__(self,kfile, outpath):
        self.kfile = kfile
        self.store = os.path.join(outpath, kfile.split('/')[-1].replace('.json',''))
        self.metadata = {}
        self.generator = {}

    def get_kfile(self):
        f = open(self.kfile,'r')
        refs = json.load(f)
        f.close()
        return refs

    def deconstruct(self,refs):

        # Setup metadata dict
        keywords = ['time','lat','lon','.zarray','zgroup','.zattrs']
        for key in refs.keys():
            if key == 'refs':
                self.metadata[key] = {}
            else:
                self.metadata[key] = refs[key]
        
        # Setup vars dict
        self.vars = {}
        self.files = ['']
        for key in refs['refs'].keys():
            try:
                firstpart, secondpart = key.split('/')
                if firstpart in keywords or secondpart[0] == '.':
                    self.metadata['refs'][key] = refs['refs'][key]
                else:
                    #print(firstpart, secondpart)
                    #x=input()
                    variable = firstpart
                    if variable not in self.vars:
                        self.vars[variable] = Variable(variable, self.store)
                    self.vars[variable].update(secondpart, refs['refs'][key])
                    if refs['refs'][key][0] != self.files[-1]:
                        self.files.append(refs['refs'][key][0])

            except ValueError:
                self.metadata['refs'][key] = refs['refs'][key] 
    
    def make_store(self):
        if not os.path.isdir(self.store):
            os.makedirs(self.store)

    def write_meta(self):
        meta = os.path.join(self.store, 'meta.json' )
        self.metadata['vars'] = self.generator
        self.metadata['files'] = self.files[1:]
        if not os.path.isfile(meta):
            os.system(f'touch {meta}')
        f = open(meta, 'w')
        f.write(json.dumps(self.metadata))
        f.close()

    def write_ncs(self):
        for var in self.vars.values():
            var.pack_gen()
            var.write_json()
            entry = var.get_entry()
            self.generator[var.var] = entry

    def process(self):
        self.make_store()
        refs = self.get_kfile()
        self.deconstruct(refs)
        self.write_ncs()
        self.write_meta()
