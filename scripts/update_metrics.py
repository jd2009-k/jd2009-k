#!/usr/bin/env python3
"""Render honest GitHub profile metrics from public data (stdlib only)."""
import html, json, math, os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

USER=os.environ.get("PROFILE_USERNAME","jd2009-k")
TOKEN=os.environ.get("GITHUB_TOKEN","")
DIR=Path(__file__).resolve().parents[1]/"assets"
DIR.mkdir(parents=True,exist_ok=True)
PALETTE=["#56e5b4","#66bdf4","#ffbd76","#aa99f5","#f18eab","#91dc9f"]

def esc(v):return html.escape(str(v),quote=True)
def text(x,y,v,size=20,color="#b9d5db",anchor="start"):
 return f'<text x="{x}" y="{y}" font-family="monospace" fill="{color}" font-size="{size}" text-anchor="{anchor}">{esc(v)}</text>'
def svg(w,h,b,light=False):
 bg="#f4faf8" if light else "#0c1721"
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" rx="20" fill="{bg}"/>{b}</svg>\n'
def save(name,source):
 (DIR/name).write_text(source,encoding="utf-8")
 print("Updated:",name)
def get(url,body=None):
 h={"Accept":"application/vnd.github+json","User-Agent":"jd2009-k-profile-graphics","X-GitHub-Api-Version":"2022-11-28"}
 if TOKEN:h["Authorization"]="Bearer "+TOKEN
 data=None
 if body is not None:
  data=json.dumps(body).encode("utf8")
  h["Content-Type"]="application/json"
 with urlopen(Request(url,data=data,headers=h),timeout=20) as r:
  return json.load(r)
def public_repos():
 repos=[]
 for p in range(1,6):
  batch=get(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={p}")
  if not isinstance(batch,list):break
  repos += [r for r in batch if not r.get("private") and not r.get("fork")]
  if len(batch)<100:break
 return repos
def draw_stats(user,repos):
 values=[("PUBLIC REPOS",user.get("public_repos",len(repos))),
         ("STARS RECEIVED",sum(x.get("stargazers_count",0) for x in repos)),
         ("FOLLOWERS",user.get("followers",0))]
 for light in (False,True):
  fg="#14333b" if light else "#ebfff5"
  sub="#53737b" if light else "#9bbfc5"
  b=text(38,46,"GITHUB / OPEN SOURCE SNAPSHOT",22,"#157d62" if light else "#65e9b9")
  for i,(label,value) in enumerate(values):
   x=184+366*i
   b+=text(x,156,value,66,fg,"middle")
   b+=text(x,209,label,18,sub,"middle")
  b+=text(1058,250,"VERIFIED PUBLIC GITHUB DATA",14,sub,"end")
  save("stats-light.svg" if light else "stats-dark.svg",svg(1100,270,b,light))
def draw_langs(repos):
 totals={}
 for repo in repos[:100]:
  try:
   langs=get(repo["languages_url"])
   if isinstance(langs,dict):
    for k,v in langs.items():totals[k]=totals.get(k,0)+int(v)
  except (HTTPError,URLError,KeyError,ValueError) as exc:
   print("Language endpoint unavailable:",str(exc)[:120])
 order=sorted(totals.items(),key=lambda x:x[1],reverse=True)
 total=sum(totals.values())
 if not total:return
 b=text(42,43,"LANGUAGES / GITHUB REPOSITORY BYTES",22,"#65e7b7")
 b+='<rect x="43" y="65" width="1014" height="24" rx="10" fill="#264650"/>'
 offset=43
 for i,(name,num) in enumerate(order):
  width=1014*num/total
  b+=f'<rect x="{offset:.2f}" y="65" width="{width:.2f}" height="24" fill="{PALETTE[i%len(PALETTE)]}"/>'
  offset+=width
 for i,(name,num) in enumerate(order[:5]):
  x=44+204*i
  b+=f'<circle cx="{x}" cy="134" r="7" fill="{PALETTE[i%len(PALETTE)]}"/>'
  b+=text(x+15,139,f"{name} {num/total:.0%}",16)
 b+=text(1055,190,"Measured code bytes, not proficiency",14,"#95b9c0","end")
 save("languages.svg",svg(1100,209,b))
 n=max(3,min(6,len(order)))
 data=order[:6]
 angles=[-math.pi/2+2*math.pi*i/n for i in range(n)]
 def pts(radius):
  return " ".join(f"{306+math.cos(a)*r:.2f},{283+math.sin(a)*r:.2f}" for a,r in zip(angles,radius))
 g=text(35,45,"REPOSITORY LANGUAGE RADAR",20,"#63eab7")
 for ring in range(1,5):
  g+=f'<polygon points="{pts([ring*40]*n)}" fill="none" stroke="#305660"/>'
 for i,a in enumerate(angles):
  lx=306+205*math.cos(a)
  ly=283+205*math.sin(a)
  g+=f'<line x1="306" y1="283" x2="{306+160*math.cos(a):.1f}" y2="{283+160*math.sin(a):.1f}" stroke="#305660"/>'
  g+=text(f"{lx:.1f}",f"{ly:.1f}",data[i][0][:12] if i<len(data) else "—",15,"#b5d7de","middle")
 scale=data[0][1] if data else 1
 radii=[160*v/scale for _,v in data]+[0]*(n-len(data))
 g+=f'<polygon points="{pts(radii)}" fill="#63c5f6" fill-opacity=".24" stroke="#63c5f6" stroke-width="3"/>'
 g+=text(306,529,"Relative language bytes · top language = outer ring",14,"#8db8be","middle")
 save("language-radar.svg",svg(616,555,g))
ALIEN=["00100100","10100101","11111111","11011011","11111111","00100100","01011010","10100101"]
def sprite(x,y,c):
 b=""
 for row,pattern in enumerate(ALIEN):
  for col,a in enumerate(pattern):
   if a=="1":b+=f'<rect x="{x+col*7}" y="{y+row*7}" width="6" height="6" fill="{c}"/>'
 return b
def draw_activity():
 if not TOKEN:
  print("GITHUB_TOKEN missing; preserving verified-data placeholders")
  return
 query={"query":"query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}","variables":{"login":USER}}
 try:
  response=get("https://api.github.com/graphql",query)
  if response.get("errors"):raise ValueError(str(response["errors"])[:200])
  calendar=response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
  weeks=calendar["weeks"]
  total=calendar["totalContributions"]
 except (HTTPError,URLError,KeyError,TypeError,ValueError) as ex:
  print("GraphQL unavailable; preserving placeholders:",str(ex)[:150])
  return
 b=text(44,50,"GITHUB / CONTRIBUTION TERRAIN",26,"#63eabc")
 b+=text(44,94,f"{total} contributions in GitHub's past-year calendar",19)
 for i,week in enumerate(weeks):
  for j,day in enumerate(week["contributionDays"]):
   count=day["contributionCount"]
   x=53+i*19+j*4
   y=209+j*9-i*2
   color="#163c34" if count==0 else "#2b8568" if count<3 else "#37b586" if count<7 else "#64e7b2"
   b+=f'<path d="M{x} {y}l8 -5l8 5l-8 5z" fill="{color}" stroke="#2c6157" stroke-width=".4"/>'
 b+=text(44,400,"Based on GitHub's reported daily contribution counts",15,"#a1c3c5")
 save("isometric-calendar.svg",svg(1100,430,b))
 a=text(42,50,"CONTRIBUTION DEFENSE / ARCADE MODE",25,"#66e8bb")
 for i,week in enumerate(weeks[-18:]):
  wcount=sum(day["contributionCount"] for day in week["contributionDays"])
  color="#21473f" if wcount==0 else "#3aa98a" if wcount<7 else "#65eabd"
  a+=sprite(44+(i%9)*114,95+(i//9)*107,color)
 a+=text(550,364,f"{total} verified contributions  ·  sprites show weekly activity",17,"#a0c5c5","middle")
 save("invaders.svg",svg(1100,400,a))
def main():
 user=get(f"https://api.github.com/users/{USER}")
 repos=public_repos()
 draw_stats(user,repos)
 draw_langs(repos)
 draw_activity()
 print("Complete for",USER)
if __name__=="__main__":main()
