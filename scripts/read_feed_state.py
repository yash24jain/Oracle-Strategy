import json,subprocess,datetime
from keccak import sel
RPC="https://ethereum-rpc.publicnode.com"
def rpc(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p})
    return json.loads(subprocess.run(["curl","-s","-m","30","-X","POST","-H","Content-Type: application/json",
        "--data",body,RPC],capture_output=True,text=True).stdout)
def call(to,sig,args=""):
    r=rpc("eth_call",[{"to":to,"data":sel(sig)+args},"latest"])
    return r.get("result") or "ERR:"+r.get("error",{}).get("message","?")
def u(h): return int(h,16) if isinstance(h,str) and h.startswith("0x") else None
def dstr(h):
    if not h.startswith("0x"): return h
    b=bytes.fromhex(h[2:]);  ln=int.from_bytes(b[32:64],'big')
    return b[64:64+ln].decode(errors="replace")

print("read() from adapter =", 0xed0852e907f876ac00, "wad ->", 0xed0852e907f876ac00/1e18, "USD\n")

FEED="0x9944d86ceb9160af5c5feb251fd671923323f8c3"
print("=== upstream feed", FEED, "===")
print("  description()  =", dstr(call(FEED,"description()")))
print("  decimals()     =", u(call(FEED,"decimals()")))
print("  version()      =", u(call(FEED,"version()")))
agg=call(FEED,"aggregator()")
print("  aggregator()   = 0x"+agg[-40:] if agg.startswith("0x") else agg)
lrd=call(FEED,"latestRoundData()")
if lrd.startswith("0x") and len(lrd)>=2+64*5:
    w=[lrd[2+64*i:2+64*(i+1)] for i in range(5)]
    ans=int(w[1],16); ua=int(w[3],16)
    now=u(rpc("eth_getBlockByNumber",["latest",False])["result"]["timestamp"])
    print(f"  latestRoundData: answer={ans} ({ans/1e8:.2f} @8dp)  updatedAt={ua}"
          f" -> {datetime.datetime.fromtimestamp(ua,datetime.UTC):%Y-%m-%d %H:%M} UTC, age={(now-ua)/3600:.2f} h")
else: print("  latestRoundData:",lrd)

OP="0x194ebc1b9b382ef0e6998caace59af843cf53b99"
print("\n=== operator", OP, "(adapter owner + OSM ward) ===")
code=rpc("eth_getCode",[OP,"latest"])["result"]
print("  code len:",(len(code)-2)//2,"bytes")
print("  runtime :",code[:200])
for sig in ["owner()","getOwners()","getThreshold()","masterCopy()","implementation()","VERSION()"]:
    r=call(OP,sig)
    if not r.startswith("ERR"): print(f"  {sig:18s} -> {r[:100]}")

SPOT="0xf3aee748355bb07CBe702B4ff8dBE6118b34e2A2"
OSM="0x89fbAe0302b8790D55fa36E6Ab09ac93F865993a"
print("\n=== OSM bud (read whitelist) ===")
for lab,a in [("Spotter",SPOT),("operator",OP),("PAXG Clipper","0x62B7a353928142A18C07026A33F8089d1c7378F4")]:
    print(f"  bud({lab:12s} {a}) = {u(call(OSM,'bud(address)','0'*24+a[2:].lower()))}")
print("\n=== Spotter ===")
print("  vat()  = 0x"+(call(SPOT,"vat()")or"")[-40:])
print("  par()  =", u(call(SPOT,"par()")))
for lab,a in [("operator",OP),("deployer","0xEEfa1a4bE1251d14CA84825CB0Be8D55f2A8251f")]:
    print(f"  wards({lab:9s}) = {u(call(SPOT,'wards(address)','0'*24+a[2:].lower()))}")
