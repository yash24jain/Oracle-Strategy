import json,subprocess,datetime
from keccak import sel
RPC="https://ethereum-rpc.publicnode.com"
OSM="0x89fbAe0302b8790D55fa36E6Ab09ac93F865993a"
ADP="0x82F5790Bd1c96790E4c3a3ebC8142bD4D6F8b1CD"
SPOT="0xf3aee748355bb07CBe702B4ff8dBE6118b34e2A2"
VAT="0xbC22e8C15bC476EF4FD0124c5A03b23607e30D2C"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    out=subprocess.run(["curl","-s","-m","30","-X","POST","-H","Content-Type: application/json",
        "--data",body,RPC],capture_output=True,text=True).stdout
    return json.loads(out)
def call(to,sig,args=""):
    r=rpc("eth_call",[{"to":to,"data":sel(sig)+args},"latest"])
    return r.get("result") or ("ERR: "+json.dumps(r.get("error")))
def u(h):
    return int(h,16) if isinstance(h,str) and h.startswith("0x") and len(h)>2 else None
def addr(h): return "0x"+h[-40:] if isinstance(h,str) and h.startswith("0x") else h

blk=u(rpc("eth_blockNumber",[])["result"])
ts=u(rpc("eth_getBlockByNumber",[hex(blk),False])["result"]["timestamp"])
print(f"block {blk}  now={datetime.datetime.utcfromtimestamp(ts):%Y-%m-%d %H:%M} UTC\n")

print("=== OSM", OSM, "===")
hop=u(call(OSM,"hop()")); zzz=u(call(OSM,"zzz()")); st=u(call(OSM,"stopped()"))
src=call(OSM,"src()")
print(f"  hop()      = {hop} sec  ({hop/3600 if hop else 0:.2f} h)")
print(f"  zzz()      = {zzz}  -> {datetime.datetime.utcfromtimestamp(zzz):%Y-%m-%d %H:%M} UTC" if zzz else f"  zzz() = {zzz}")
if zzz: print(f"               age = {(ts-zzz)/86400:.1f} days")
print(f"  stopped()  = {st}   {'<-- FROZEN' if st else '(running)'}")
print(f"  src()      = {addr(src)}   {'== PriceFeedAdapter' if addr(src).lower()==ADP.lower() else '<-- NOT the adapter'}")
print(f"  pass()     = {call(OSM,'pass()')}")
print(f"  peek()     = {call(OSM,'peek()')}")
print(f"  peep()     = {call(OSM,'peep()')}")

print("\n=== PriceFeedAdapter", ADP, "===")
own=call(ADP,"owner()")
print(f"  owner()    = {addr(own)}")
md=u(call(ADP,"maxDelay()"))
print(f"  maxDelay() = {md} sec ({md/3600 if md else 0:.2f} h)")
print(f"  priceFeed()= {addr(call(ADP,'priceFeed()'))}")
print(f"  asset()    = {addr(call(ADP,'asset()'))}")
print(f"  paused()   = {call(ADP,'paused()')}")
print(f"  read()     = {call(ADP,'read()')}")

print("\n=== is owner an EOA or a contract? ===")
for label,a in [("adapter owner",addr(own)),("OSM deployer","0xEEfa1a4bE1251d14CA84825CB0Be8D55f2A8251f"),
                ("poker EOA","0xcCdA4D0e76a6515EBa5259b029683514d0d26F35")]:
    code=rpc("eth_getCode",[a,"latest"])["result"]
    print(f"  {label:14s} {a}  code={len(code)-2} bytes -> {'CONTRACT' if len(code)>2 else 'EOA'}")

print("\n=== OSM wards (auth) ===")
for label,a in [("deployer","0xEEfa1a4bE1251d14CA84825CB0Be8D55f2A8251f"),
                ("poker","0xcCdA4D0e76a6515EBa5259b029683514d0d26F35"),
                ("adapter owner",addr(own))]:
    r=call(OSM,"wards(address)","0"*24+a[2:].lower())
    print(f"  wards({label:14s} {a}) = {u(r)}")
