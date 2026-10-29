"""Minimal read-only IDL data decoder; no networking, signer, or instruction construction."""
import base64,hashlib,struct
ALPH='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def base58(b):
 n=int.from_bytes(b,'big');s=''
 while n:n,r=divmod(n,58);s=ALPH[r]+s
 return '1'*(len(b)-len(b.lstrip(b'\0')))+s
class IDLDecoder:
 def __init__(self,idl,raw):self.raw=raw;self.at=0;self.types={t['name']:t['type']for t in idl.get('types',[])+idl.get('accounts',[])if 'type'in t}
 def get(self,n):
  b=self.raw[self.at:self.at+n];assert len(b)==n,('unexpected account length',self.at,n,len(self.raw));self.at+=n;return b
 def read(self,t):
  if isinstance(t,str):
   if t in ['pubkey','publicKey']:return base58(self.get(32))
   if t=='bool':return bool(self.get(1)[0])
   if t in ['f32','f64']:return struct.unpack('<f'if t=='f32'else'<d',self.get(int(t[1:])//8))[0]
   if t[0]in'ui'and t[1:].isdigit():return int.from_bytes(self.get(int(t[1:])//8),'little',signed=t[0]=='i')
   return self.read(self.types[t])
  if 'array'in t:return [self.read(t['array'][0])for _ in range(t['array'][1])]
  if 'defined'in t:return self.read(self.types[t['defined']['name']if isinstance(t['defined'],dict)else t['defined']])
  if 'option'in t:return self.read(t['option'])if self.get(1)[0]else None
  if 'vec'in t:return [self.read(t['vec'])for _ in range(int.from_bytes(self.get(4),'little'))]
  if t.get('kind')=='struct':return {f['name']:self.read(f['type'])for f in t['fields']}
  if t.get('kind')=='enum':
   i=self.get(1)[0];v=t['variants'][i];fields=v.get('fields',[]);return {'variant':v['name'],'fields':{f['name']:self.read(f['type'])for f in fields}if fields and isinstance(fields[0],dict)and'name'in fields[0]else[self.read(f)for f in fields]}
  raise ValueError(t)
def decode_account(idl,v,name,owner):
 assert v['owner']==owner,('wrong program owner',v['owner']);raw=base64.b64decode(v['data'][0]);entry=next((x for x in idl['accounts']if x['name']==name),None);expected=bytes(entry['discriminator'])if entry and'discriminator'in entry else hashlib.sha256(('account:'+name[:1].upper()+name[1:]).encode()).digest()[:8];assert raw[:8]==expected,(name,'discriminator mismatch')
 d=IDLDecoder(idl,raw[8:]);s=d.read(name);return {'state':s,'bytes':len(raw),'decodedBytes':d.at+8,'programOwner':owner,'discriminatorVerified':True}
