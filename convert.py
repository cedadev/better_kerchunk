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

ERRORS = {
    "File": "[FileError]"
}

VERBOSE=True

def vprint(msg, err=None):
    if VERBOSE:
        status = '[INFO]'
        if err:
            status = ERRORS[err]
        print(f'{status}: {msg}')

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

    def configure(self, chunks, msize, moffset, fileset):
        self.chunks = chunks
        self.msize = msize
        self.moffset = moffset
        self.fileset = fileset

    def update(self, key, segments):
        # Update arrays with new attributes
        if segments[0] != self.latestfile:
            self.fileids.append(self.fcounter)
            self.latestfile = segments[0]
        self.fcounter += 1
        self.keys.append(key)
        self.offsets.append(segments[1])
        self.sizes.append(segments[2])

    def get_entry(self):
        return [self.chunks, self.msize, self.moffset]

    def read_entry(self):
        jsfile = f'{self.store}/{self.var}.json'
        f = open(jsfile,'r')
        refs = json.load(f)
        f.close()
        return refs

    def unpack_gen(self):

        refs = self.read_entry()
        uniqueids     = np.array(refs['unique_ids'], dtype=int)
        uniquelengths = np.array(refs['unique_lengths'], dtype=int)

        gapids        = np.array(refs['gap_ids'],dtype=int)
        gaplengths    = np.array(refs['gap_lengths'],dtype=int)

        keys = refs['keys']
        fileids = refs['fileids']

        # Assume we've already collected the json/netcdf contents
        # Also assume we have the file arrays and everything
        sizes   = np.zeros(self.chunks, dtype=int) + self.msize
        files   = []
        offsets = np.zeros(self.chunks, dtype=int) + self.moffset

        # Extract file list
        init = 0
        for x, f in enumerate(self.fileset):
            for y in range(init, fileids[x]):
                files.append(f)
            init = fileids[x]

        # Get sizes
        sizes[uniqueids] = uniquelengths
        offsets[gapids] = gaplengths

        # Offsets currently reversed

        chunk_array = np.reshape(np.transpose([files, np.array(offsets,dtype=int), np.array(sizes, dtype=int)]), (self.chunks, 3))
        unpacked_refs = {}
        for c in range(self.chunks):
            unpacked_refs[f'{self.var}/{keys[c]}'] = list(chunk_array[c])

        return unpacked_refs
        
    def pack_gen(self):
        vprint(f'Packing {self.var}')
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
        self.fileids.append(self.fcounter)
        refs = {
            'unique_ids':self.uniqueids,
            'unique_lengths':self.uniquelengths,
            'gap_ids':self.gapids,
            'gap_lengths':self.gaplengths,
            'keys':self.keys,
            'fileids':self.fileids[1:],
        }
        f = open(jsfile,'w')
        f.write(json.dumps(refs, cls=NumpyArrayEncoder))
        f.close()
        vprint(f'Written json {jsfile}')



class Converter:
    def __init__(self,kfile, outpath):
        self.kfile = kfile
        self.store = os.path.join(outpath, kfile.split('/')[-1].replace('.json','')) + '.kst'
        self.metadata = {}
        self.generator = {}
        self.vars = {}

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
        self.files = ['']
        for key in refs['refs'].keys():
            try:
                firstpart, secondpart = key.split('/')
                if firstpart in keywords or secondpart[0] == '.' or len(refs['refs'][key]) > 3:
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
        vprint('Ensuring store exists')
        if not os.path.isdir(self.store):
            os.makedirs(self.store)

    def write_meta(self):
        vprint('Writing metadata')
        meta = os.path.join(self.store, 'meta.json' )
        self.metadata['vars'] = self.generator
        self.metadata['files'] = self.files[1:]
        if not os.path.isfile(meta):
            os.system(f'touch {meta}')
        f = open(meta, 'w')
        f.write(json.dumps(self.metadata))
        f.close()

    def read_meta(self):
        meta = os.path.join(self.store, 'meta.json' )
        f = open(meta,'r')
        meta = json.load(f)
        f.close()

        self.metadata = {
            'version': meta['version'],
            'refs':meta['refs']
        }

        for var in meta['vars'].keys():
            self.vars[var] = Variable(var, self.store)
            self.vars[var].configure(*meta['vars'][var], meta['files'])

    def write_vars(self):
        vprint('Writing variables')
        for var in self.vars.values():
            var.pack_gen()
            var.write_json()
            entry = var.get_entry()
            self.generator[var.var] = entry

    def read_vars(self):
        vprint('Reading variables')
        refs = {}
        for var in self.vars.values():
            refs = {**refs, **var.unpack_gen()}
        return refs

    def construct(self):
        vprint('Merging and constructing')
        refs = self.read_vars()
        self.metadata['refs'] = {**self.metadata['refs'], **refs}

    def process(self):
        self.make_store()
        refs = self.get_kfile()
        self.deconstruct(refs)
        self.write_vars()
        self.write_meta()
        vprint('Success')

    def cache_construct(self):
        f = open(self.kfile.replace('.json','_rec.json'),'w')
        f.write(json.dumps(self.metadata, cls=NumpyArrayEncoder))
        f.close()

    def verify_meta(self):
        vprint('Attempting Verification')
        original = self.get_kfile()
        translated = self.metadata
        outcount = 0
        for key in original.keys():
            if key != 'refs':
                if translated[key] == original[key]:
                    outcount += 1
            else:
                outcount += 1
        vprint(f'Metadata Accuracy: {outcount*100/len(original.keys()):.1f} %')

        incount = 0
        for key in original['refs'].keys():
            p1 = str(translated['refs'][key][1]) == str(original['refs'][key][1])
            p2 = str(translated['refs'][key][2]) == str(original['refs'][key][2])
            if p1 and p2:
                incount += 1
        vprint(f'Refs Accuracy: {incount*100/len(original["refs"].keys()):.1f} %')


    def load(self, cache=None, verify=None):
        self.read_meta()
        self.construct()
        vprint('Success')
        if cache:
            self.cache_construct()
        if verify:
            self.verify_meta()
        return self.metadata