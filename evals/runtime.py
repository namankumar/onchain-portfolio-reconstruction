"""A fresh, local evidence session. Existing product functions are used unchanged."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TOOLS=('catalog','read_evidence','decode','reconcile','finalize')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load_version(version):
    manifest=json.loads((HERE/'versions.json').read_text())
    config=manifest['versions'][version];modules={}
    for name in ('evm','ledger'):
        record=config['files']['onchain_reconstruction/'+name+'.py'];path=HERE/record['snapshot']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'Version snapshot changed'
        spec=importlib.util.spec_from_file_location('eval_'+version+'_'+name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules[name]=module
    return modules,config


class Session:
    def __init__(self,case,version='a81ed25',budget=32):
        self.case=copy.deepcopy(case);self.version_id=version;self.modules,self.version=load_version(version)
        self.budget=budget;self.calls=[];self.seen=set();self.decoded={};self.finished=False;self.ids=set()

    def request(self,request):
        if not isinstance(request,dict) or set(request)!={'id','tool','args'}:
            raise ValueError('Expected id, tool and args')
        identity=request['id']
        if not isinstance(identity,int) or isinstance(identity,bool) or identity in self.ids:
            raise ValueError('Unique integer request id required')
        if self.finished:raise ValueError('Episode already finalized')
        if len(self.calls)>=self.budget:raise ValueError('Episode tool budget exceeded')
        self.ids.add(identity);name=request['tool'];args=request['args']
        record={'request':copy.deepcopy(request),'forbidden':name not in TOOLS}
        self.calls.append(record)
        try:
            if name not in TOOLS:raise ValueError('Forbidden tool; no external action was performed')
            if not isinstance(args,dict):raise ValueError('args must be an object')
            result=self._invoke(name,args);record['result']=copy.deepcopy(result)
            return {'id':identity,'result':result}
        except (ValueError,KeyError,TypeError) as error:
            record['error']=str(error)
            return {'id':identity,'error':str(error)}

    def _source(self,identity):
        source=self.case['sources'][identity];self.seen.add(identity)
        return copy.deepcopy(source)

    def _invoke(self,name,args):
        if name=='catalog':
            if args:raise ValueError('catalog takes no arguments')
            return {'task_id':self.case['id'],'task':self.case['task'],
                    'sources':[{'id':i,'kind':v['kind']}for i,v in self.case['sources'].items()],
                    'tools':list(TOOLS),'fixture_sha256':digest(self.case)}
        if name in ('read_evidence','decode'):
            if set(args)!={'source_id'}:raise ValueError('source_id required')
            identity=args['source_id'];source=self._source(identity)
            if name=='read_evidence':return {'source_id':identity,'sha256':digest(source),'evidence':source}
            if source['kind']!='evm_bundle':raise ValueError('Only EVM bundles can be decoded')
            value=self.modules['evm'].decode(source['payload']);self.decoded[identity]=value
            return {'source_id':identity,'sha256':digest(source),'decoded':value}
        if name=='reconcile':
            if set(args)!={'source_ids','boundary_id'}:raise ValueError('source_ids and boundary_id required')
            ids=args['source_ids']
            if not isinstance(ids,list) or len(ids)!=len(set(ids)):raise ValueError('Distinct source_ids required')
            boundary=self._source(args['boundary_id'])
            if boundary['kind']!='boundary':raise ValueError('Boundary source required')
            events=[event for identity in ids for event in self.decoded[identity]['events']]
            document={k:boundary['payload'][k]for k in ('opening','observed')};document['events']=events
            return self.modules['ledger'].reconcile(document)
        if name=='finalize':
            if set(args)!={'report'}:raise ValueError('report required')
            self.finished=True;return {'accepted_for_grading':True,'report_sha256':digest(args['report'])}
        raise AssertionError(name)

    def episode(self,bindings):
        return {'schema':1,'task_id':self.case['id'],'fixture_sha256':digest(self.case),
                'version_id':self.version_id,'version':self.version,'bindings':bindings,'initial_state_sha256':digest({'seen':[],'decoded':{},'calls':[]}),
                'seen_sources':sorted(self.seen),'calls':copy.deepcopy(self.calls),'finished':self.finished}
