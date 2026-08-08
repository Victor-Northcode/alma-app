"""Sixth pass: does a starvation valve close the 60-day silences, and at what price?

Rule under test = the recommended rule plus: if nothing has fired for STARVE
days, the floor drops to RELAX for the next candidate only.
"""
import random, statistics, sys
from collections import Counter
from datetime import datetime, timezone
sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")
from alma.engine import natal, transits
from alma.engine.timeutil import _julian_day, resolve

random.seed(11)
PLACES = [("Europe/Warsaw",50.06,19.94),("America/New_York",40.71,-74.01),
          ("Asia/Seoul",37.57,126.98),("Australia/Sydney",-33.87,151.21),
          ("America/Sao_Paulo",-23.55,-46.63),("Africa/Lagos",6.52,3.38),
          ("Europe/Madrid",40.42,-3.70),("Asia/Kolkata",19.08,72.88)]
COHORT=[]
for i in range(24):
    y,mo,d = random.randint(1962,2006), random.randint(1,12), random.randint(1,28)
    tz,lat,lon = PLACES[i%len(PLACES)]
    h,mi = (None,None) if i%7==0 else (random.randint(0,23), random.choice([0,15,30,45]))
    COHORT.append((f"c{i:02d}",y,mo,d,h,mi,tz,lat,lon))

START=_julian_day(datetime(2026,8,7,tzinfo=timezone.utc))
END=_julian_day(datetime(2027,8,7,tzinfo=timezone.utc))
DAYS=365; SLOW=set(transits.SLOW_BODIES)

def sim(hits, floor, slow_floor, gap, cap, starve=None, relax=None):
    # every candidate day, with its best weight, kept at the RELAX floor so the
    # valve has something to reach for
    base = relax if relax is not None else floor
    cand = {}
    for h in hits:
        d=int(h.exact_jd-START)
        if 0<=d<DAYS and h.weight>=base and h.weight>cand.get(d,(0,))[0]:
            cand[d]=(h.weight,"exact")
        if h.transiting in SLOW and h.enters_jd is not None and h.weight>=min(base,slow_floor):
            de=int(h.enters_jd-START)
            if 0<=de<DAYS and h.weight>cand.get(de,(0,))[0]:
                cand[de]=(h.weight,"opens")
    fired=[]; month=Counter(); valve=0
    last=-10**6
    for d in sorted(cand):
        w,kind=cand[d]
        starving = starve is not None and (d-last)>=starve
        need = relax if starving else (slow_floor if kind=="opens" else floor)
        if w < need: continue
        if fired and d-fired[-1]<gap: continue
        m=d//30
        if month[m]>=cap: continue
        month[m]+=1; fired.append(d); last=d
        if starving and w < (slow_floor if kind=="opens" else floor): valve+=1
    gaps=[b-a for a,b in zip(fired,fired[1:])]
    lead=fired[0] if fired else DAYS; tail=DAYS-fired[-1] if fired else DAYS
    return len(fired), max(gaps+[lead,tail]) if fired else DAYS, valve

charts={}
for (l,y,mo,d,h,mi,tz,lat,lon) in COHORT:
    charts[l]=natal.compute(moment=resolve(year=y,month=mo,day=d,hour=h,minute=mi,
                            tz_name=tz,on_ambiguous="earlier"),latitude=lat,longitude=lon)
H={k:transits.scan(c,start_jd=START,end_jd=END,reference_jd=START) for k,c in charts.items()}

print(f"{'variant':>46s} | {'med/yr':>7s} {'max/yr':>7s} {'/wk max':>8s} | {'worst silence':>14s} | {'valve fires':>11s}")
for name,kw in [
    ("no valve (0.35/0.30/gap3/cap10)", dict(floor=.35,slow_floor=.30,gap=3,cap=10)),
    ("valve: 21 days → floor 0.25",     dict(floor=.35,slow_floor=.30,gap=3,cap=10,starve=21,relax=.25)),
    ("valve: 21 days → floor 0.20",     dict(floor=.35,slow_floor=.30,gap=3,cap=10,starve=21,relax=.20)),
    ("valve: 14 days → floor 0.25",     dict(floor=.35,slow_floor=.30,gap=3,cap=10,starve=14,relax=.25)),
    ("valve: 14 days → floor 0.20",     dict(floor=.35,slow_floor=.30,gap=3,cap=10,starve=14,relax=.20)),
]:
    rows=[sim(h,**kw) for h in H.values()]
    p=sorted(r[0] for r in rows)
    print(f"{name:>46s} | {statistics.median(p):7.0f} {p[-1]:7d} {p[-1]/52:8.2f} | "
          f"{max(r[1] for r in rows):14d} | {sum(r[2] for r in rows):11d}")
