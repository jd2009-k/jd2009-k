#!/usr/bin/env python3
"""Self-hosted GitHub profile SVGs using verified public data and GitHub Actions.

Uses only the Python standard library. Run --init-offline for honest launch
placeholders; an online run retrieves public REST / GraphQL information.
"""
from __future__ import annotations
import html
import json
import math
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = os.environ.get('PROFILE_USERNAME', 'jd2009-k')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
ASSETS = Path(__file__).resolve().parents[1] / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
COLORS = ['#4ce0af','#60c4ff','#f5bf76','#b3a4ff','#f38ba6','#75d3c7','#c9df8a','#e9a6fd']


def esc(text):
    return html.escape(str(text), quote=True)


def svg(width, height, body, title, *, light=False, rounded=22):
    bg, edge, ink = ('#f4faf9','#acc7c6','#142d37') if light else ('#0c151e','#294a50','#e5fcf4')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title>'
            f'<rect width="{width}" height="{height}" rx="{rounded}" fill="{bg}"/>'
            f'<rect x="1.5" y="1.5" width="{width-3}" height="{height-3}" rx="{rounded-2}" fill="none" stroke="{edge}" stroke-width="1.5"/>'
            f'{body}</svg>')


def tx(x, y, content, size=20, color='#b7d6d7', *, weight=400, anchor='start', family='monospace'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-family="{family}" font-weight="{weight}" text-anchor="{anchor}">{esc(content)}</text>')


def write(filename, source):
    (ASSETS / filename).write_text(source + '\n', encoding='utf8')
    print('Rendered', filename)


def get_json(url, body=None):
    h={'User-Agent':'jay-donga-profile/2.0','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    if TOKEN:
        h['Authorization']='Bearer '+TOKEN
    data=None
    if body is not None:
        h['Content-Type']='application/json'
        data=json.dumps(body).encode()
    with urlopen(Request(url, headers=h, data=data), timeout=25) as response:
        return json.load(response)


def github_repos():
    results=[]
    for page in range(1,11):
        page_repos=get_json(f'https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(page_repos,list):
            raise ValueError('Unexpected GitHub repository response')
        results.extend(r for r in page_repos if not r.get('fork') and not r.get('private'))
        if len(page_repos)<100:
            break
    return results


def stats(repos_count, stars, followers, *, verified):
    for light in (False, True):
        ink='#153642' if light else '#e7fbf4'
        muted='#527786' if light else '#89b1bb'
        b=tx(48,60,'GITHUB / OPEN SOURCE SNAPSHOT',23,'#259b78' if light else '#5deac0',weight=700)
        values=[('PUBLIC REPOSITORIES',str(repos_count)),('STARS RECEIVED',str(stars)),('FOLLOWERS',str(followers))]
        for i,(label,value) in enumerate(values):
            x=185+i*363
            b+=tx(x,151,value,64,ink,weight=700,anchor='middle',family='Arial,Helvetica,sans-serif')
            b+=tx(x,201,label,19,muted,anchor='middle')
        b+='<path d="M366 90v118M733 90v118" stroke="#507c80" opacity=".38"/>'
        b+=tx(1074,243,'LIVE GITHUB DATA' if verified else 'INITIAL SNAPSHOT · FOLLOWERS PENDING',13,muted,anchor='end')
        write('stats-light.svg' if light else 'stats-dark.svg',svg(1100,268,b,'Public GitHub account statistics',light=light))


def languages(lang_bytes):
    if not lang_bytes:
        b=tx(44,55,'CODE LANGUAGE DISTRIBUTION',25,'#61e4b7',weight=700)
        b+=tx(44,116,'Awaiting first GitHub Actions metrics refresh',20)
        b+='<rect x="44" y="149" width="1012" height="21" rx="10" fill="#203b46"/>'
        write('languages.svg',svg(1100,209,b,'Language data pending, not estimated'))
        write('language-radar.svg',radar_languages({},'pending'))
        return
    vals=sorted(lang_bytes.items(),key=lambda v:v[1],reverse=True)
    total=sum(x[1] for x in vals)
    b=tx(42,45,'LANGUAGES / CODE BYTES',21,'#63e6ba',weight=700)
    b+='<rect x="43" y="65" width="1014" height="24" rx="12" fill="#213541"/>'
    offset=43.0
    for i,(label,count) in enumerate(vals):
        length=1014*count/total
        b+=f'<rect x="{offset:.2f}" y="65" width="{length:.2f}" height="24" fill="{COLORS[i%len(COLORS)]}"/>'
        offset+=length
    for i,(label,count) in enumerate(vals[:5]):
        x=52+208*i
        b+=f'<circle cx="{x}" cy="131" r="7" fill="{COLORS[i%len(COLORS)]}"/>'
        b+=tx(x+17,137,f'{label} {100*count/total:.0f}%',17)
    b+=tx(1056,185,'Measured using GitHub language bytes · not skill level',13,'#8db4be',anchor='end')
    write('languages.svg',svg(1100,207,b,'Public repository language proportions'))
    write('language-radar.svg',radar_languages(lang_bytes,'live'))


def polar(cx,cy,r,angle):
    return cx+math.cos(angle)*r,cy+math.sin(angle)*r


def polyline(points):
    return ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)


def radar_grid(cx,cy,rad,n, labels, values=None, palette='#5ce5b6'):
    # Polygons are decorative comparisons, not percentages of expertise.
    parts=[]
    angles=[-math.pi/2+math.tau*i/n for i in range(n)]
    for scale in (0.25,0.5,0.75,1.0):
        pts=[polar(cx,cy,rad*scale,angle) for angle in angles]
        parts.append(f'<polygon points="{polyline(pts)}" fill="none" stroke="#294f58" stroke-width="1.5"/>')
    for angle in angles:
        x,y=polar(cx,cy,rad,angle)
        parts.append(f'<path d="M{cx},{cy}L{x:.2f},{y:.2f}" stroke="#2a535c"/>')
    if values:
        points=[polar(cx,cy,rad*values[i],a) for i,a in enumerate(angles)]
        parts.append(f'<polygon points="{polyline(points)}" fill="{palette}" fill-opacity=".21" stroke="{palette}" stroke-width="3"/>')
        for x,y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{palette}"/>')
    for i,(label,angle) in enumerate(zip(labels,angles)):
        x,y=polar(cx,cy,rad+38,angle)
        anchor='middle' if abs(x-cx)<16 else 'start' if x>cx else 'end'
        parts.append(tx(f'{x:.1f}',f'{y+5:.1f}',label,17,'#bed9de',anchor=anchor))
    return ''.join(parts)


def radar_languages(lang_bytes,state):
    b=tx(35,47,'REPOSITORY LANGUAGE RADAR',19,'#63e6ba',weight=700)
    if lang_bytes:
        vals=sorted(lang_bytes.items(),key=lambda a:a[1],reverse=True)[:6]
        total=sum(lang_bytes.values())
        # Proportion of all measured source bytes on linear radial scale.
        n=max(3,len(vals))
        labels=[x[0][:13] for x in vals]+['—']*(n-len(vals))
        shares=[x[1]/total for x in vals]+[0]*(n-len(vals))
        # 3d chart legibility: scale relative to most used language, note this fact below.
        top=max(shares)
        scaled=[n/top if top else 0 for n in shares]
        b+=radar_grid(307,290,163,n,labels,scaled,'#5abefa')
        b+=tx(305,528,'Relative byte counts; largest language = outer ring',13,'#91b9c2',anchor='middle')
    else:
        b+=radar_grid(307,290,163,6,['C++','TypeScript','JavaScript','C','CSS','HTML'],None,'#5abefa')
        b+=tx(307,528,'No measured data yet · workflow will populate',14,'#91b9c2',anchor='middle')
    return svg(616,555,b,'Language radar from public GitHub repositories' if lang_bytes else 'Language radar pending source data')


def focus_radar():
    b=tx(35,47,'AREAS I AM EXPLORING',19,'#63e6ba',weight=700)
    # Equal radius: categorical interests only; no invented self-grades.
    b+=radar_grid(306,290,163,6,['Web apps','React / TS','Supabase','Security','C++ / DSA','UI / UX'],[.82]*6)
    b+=tx(306,528,'Equal-radius topics · no proficiency score',14,'#91b9c2',anchor='middle')
    write('focus-radar.svg',svg(616,555,b,'Radar of areas of current learning and building'))


def empty_contribution_graphics():
    b=tx(48,64,'GITHUB CONTRIBUTION TERRAIN',27,'#65e8bc',weight=700)
    b+=tx(48,119,'Isometric calendar generates from your real contribution history.',21)
    b+=tx(48,161,'Run Actions → Refresh GitHub profile visuals to populate it.',19,'#87aeb8')
    b+='<path d="M58 254l160 -90 160 90 -160 90Z" fill="#193f41" stroke="#3da981" stroke-width="3"/>'
    b+='<path d="M218 344v37L58 289v-35M218 344v37l160-92v-35" fill="#163439" stroke="#3da981" stroke-width="2"/>'
    b+=tx(496,289,'AWAITING VERIFIED GITHUB DATA',23,'#77dfb7',weight=700)
    b+=tx(496,325,'No contribution counts have been inferred.',18)
    write('isometric-calendar.svg',svg(1100,430,b,'Isometric calendar pending verified contribution data'))
    b=tx(47,55,'CONTRIBUTION DEFENSE / ARCADE MODE',25,'#72eac0',weight=700)
    for i in range(11):
        x=57+i*83
        y=111+(i%2)*24
        b+=pixel_alien(x,y,'#216356' if i%2 else '#2f826e')
    b+=tx(548,292,'INSERT VERIFIED CONTRIBUTION SIGNAL TO START',20,'#a7d8ce',anchor='middle')
    b+=tx(548,330,'Daily contributions power this graphic after the workflow runs',16,'#80acb9',anchor='middle')
    b+='<path d="M545 353v-18M517 361h56M525 379h40" stroke="#6ae5b5" stroke-width="5"/>'
    write('invaders.svg',svg(1100,409,b,'Retro contribution-themed graphic pending real GitHub data'))


def pixel_alien(x,y,color):
    pattern=['00100100','10100101','11111111','11011011','11111111','00100100','01011010','10100101']
    rects=[]
    for row,line in enumerate(pattern):
        for col,c in enumerate(line):
            if c=='1':
                rects.append(f'<rect x="{x+col*7}" y="{y+row*7}" width="6" height="6" fill="{color}"/>')
    return ''.join(rects)


def contribution_info():
    if not TOKEN:
        print('No GITHUB_TOKEN: activity graphics remain pending')
        return None
    query={'query':'query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}','variables':{'login':USERNAME}}
    try:
        body=get_json('https://api.github.com/graphql',query)
        if body.get('errors'):
            raise ValueError(body['errors'])
        return body['data']['user']['contributionsCollection']['contributionCalendar']
    except (KeyError, TypeError, ValueError, HTTPError, URLError, OSError) as exc:
        print('Contribution GraphQL unavailable:',str(exc)[:200])
        return None


def contribution_days(data):
    return sorted(
        [dict(day) for week in data.get('weeks',[]) for day in week.get('contributionDays',[])],
        key=lambda d: d.get('date','')
    )


def streak_metrics(days):
    if not days:
        return 0, 0, 0, 0.0
    counts=[max(0,int(d.get('contributionCount',0))) for d in days]
    longest=run=0
    for count in counts:
        run=run+1 if count else 0
        longest=max(longest,run)
    last=len(counts)-1
    # Today can still be in progress. A positive yesterday is a live streak.
    if last>=0 and not counts[last]:
        last-=1
    current=0
    while last>=0 and counts[last]:
        current+=1
        last-=1
    return current, longest, max(counts), sum(counts)/len(counts)


def pxpoints(points):
    return ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)


def voxel(x,y,height,top,right,left,day,count,*,glow=False):
    # Isometric cell: the color-coded *top* represents one actual contribution day.
    # Height is a bounded visual encoding of the day count; values are in title.
    W,H=10.0,5.3
    A=(x,y-height);B=(x+W,y-H-height);C=(x+2*W,y-height);D=(x+W,y+H-height)
    back=(x+2*W,y+H);front=(x+W,y+2*H);near=(x,y+H)
    dur='6s' if count else '10s'
    pulse=f'<animate attributeName="opacity" values=".80;1;.80" dur="{dur}" begin="-{(round(x+y)%33)/7:.2f}s" repeatCount="indefinite"/>' if count else ''
    return (f'<g class="voxel"><title>{esc(day)}: {count} contributions</title>'
            f'<polygon points="{pxpoints((A,D,front,near))}" fill="{left}"/>'
            f'<polygon points="{pxpoints((D,C,back,front))}" fill="{right}"/>'
            f'<polygon points="{pxpoints((A,B,C,D))}" fill="{top}" stroke="#0b2520" stroke-width=".75">{pulse}</polygon></g>')


def dark_shell(width,height,body,title,radius=16):
    return svg(width,height,body,title,light=False,rounded=radius)


def contribution_isometric(data, phase=0.0, *, write_file=True):
    """Full-size 3D-looking block terrain; readable across narrow GitHub pages.

    Empty days have a visible (muted) tile; height and green intensity encode
    ONLY verified counts. A moving light sweep is baked into GIF frames.
    """
    weeks = data.get('weeks', [])[-53:]
    days = contribution_days(data)
    cur, longest, high, avg = streak_metrics(days)
    total = int(data.get('totalContributions', 0))
    active = sum(int(d.get('contributionCount', 0)) > 0 for d in days)
    phase = phase % 1.0
    b = '''<defs>
    <linearGradient id="floor" x2=".1" y2="1"><stop stop-color="#0d1c23"/><stop offset="1" stop-color="#13282b"/></linearGradient>
    <linearGradient id="pulse" x1="0" x2="1"><stop stop-color="#10c98f" stop-opacity="0"/><stop offset=".5" stop-color="#43fec3" stop-opacity=".17"/><stop offset="1" stop-color="#10c98f" stop-opacity="0"/></linearGradient>
    </defs>'''
    b += '<rect x="36" y="94" width="1028" height="408" rx="20" fill="url(#floor)" stroke="#284b50"/>'
    b += '<path d="M56 84H1044" stroke="#27494b"/>'
    b += tx(49,50,'3D CONTRIBUTION TERRAIN',30,'#73ebbb',weight=700)
    b += tx(1042,49,'LIVE GITHUB / 53 WEEKS',18,'#8ebac2',anchor='end')
    b += tx(60,128,'Every tile = 1 real day. Brighter and taller = more contributions.',16,'#83b6b5')
    # True calendar-style 53 x 7 footprint, expanded in both visible axes.
    # Column and weekday basis vectors are angled relative to each other.
    # Each cell has three individually shaded surfaces and a measurable height.
    def P(col, row):
        return (162 + col * 14.0 - row * 16.3, 174 + col * 2.40 + row * 22.4)
    def poly(points, color, stroke=None, sw=0):
        ps = ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
        return f'<polygon points="{ps}" fill="{color}"{s}/>'
    # Subtle deck/base, with explicit 3D side walls.
    a=P(-0.65,-0.55); z=P(53,-0.55); q=P(53,7); w=P(-0.65,7)
    b += poly([a,z,q,w],'#0a1a20','#32665b',2)
    b += poly([w,q,(q[0],q[1]+20),(w[0],w[1]+20)],'#122d2c')
    b += poly([z,q,(q[0],q[1]+20),(z[0],z[1]+20)],'#153f3a')
    grid=[]
    light_x = 0.1 + phase*52.0
    for col, week in enumerate(weeks):
        for row, day in enumerate(week.get('contributionDays', [])):
            count=max(0,int(day.get('contributionCount',0)))
            x,y=P(col,row)
            h = 2.8 if count==0 else min(88, 7 + 9.0*math.sqrt(count))
            # Tiny sculpted voxel with two face shades and a top polygon.
            # No fake contribution values: empty days are visible, but low.
            A=(x,y-h); B=(x+13,y+2.22-h); C=(x-2.6,y+19.0-h); D=(x+10.4,y+21.2-h)
            glow = max(0,1-abs(col-light_x)/8.0)*.19
            if count == 0:
                top='#20433f' if (col+row)%2 else '#1a3938'
                front='#112d2e'; side='#163534'
                if glow>.08: top='#275148'
            elif count <= 2:
                top='#39ad75'; front='#206b50'; side='#2c885f'
            elif count <= 6:
                top='#5cda93';front='#288963';side='#37a879'
            elif count <= 14:
                top='#76f2aa';front='#2aa875';side='#4fd393'
            else:
                top='#b1ffd1';front='#36b981';side='#66f2a4'
            tip=esc(day.get('date',''))
            entry = f'<g><title>{tip}: {count} contributions</title>'
            entry += poly([C,D,(D[0],D[1]+h), (C[0],C[1]+h)],front)
            entry += poly([B,D,(D[0],D[1]+h),(B[0],B[1]+h)],side)
            entry += poly([A,B,D,C],top,'#0b2326',.6)
            if count and abs(col-light_x)<1.5:
                entry += poly([A,B,D,C],'#b1ffe4') if glow>.16 else ''
            entry += '</g>'
            grid.append((col*1.0+row*.09,entry))
    # Paint back to front to preserve neighboring cell occlusion.
    for _,g in sorted(grid,key=lambda x:x[0]): b+=g
    b += tx(68,471,f'{total} VERIFIED CONTRIBUTIONS  /  {active} ACTIVE DAYS',18,'#83edc1',weight=700)
    b += tx(1040,473,'DATA FROM GITHUB',16,'#6caba9',anchor='end')
    # Big bottom metrics row instead of microscopic text in a side column.
    labels=[('CURRENT STREAK',f'{cur} days'),('BEST STREAK',f'{longest} days'),('PEAK DAY',str(high)),('DAILY AVERAGE',f'{avg:.2f}')]
    for i,(lab,val) in enumerate(labels):
        x=48+i*264
        b+=f'<rect x="{x}" y="524" width="248" height="101" rx="14" fill="#10272c" stroke="#305756" stroke-width="1.6"/>'
        b+=tx(x+18,557,lab,17,'#8daebd',weight=700)
        b+=tx(x+18,606,val,36,'#8ffac4',weight=700)
    b += tx(1038,661,'JAY DONGA    //    @jd2009-k',16,'#76a1aa',anchor='end')
    doc=dark_shell(1100,680,b,'Readable animated 3D-style contribution calendar with real GitHub counts')
    if write_file: write('isometric-calendar.svg',doc)
    return doc

ALIEN_A=['00100100','10100101','11111111','11011011','11111111','00100100','01011010','10100101']
ALIEN_B=['00011000','00111100','01111110','11011011','11111111','00100100','01000010','10000001']


def alien_pixels(x,y,style,unit=4.3,pattern=ALIEN_A):
    p=[]
    for row,line in enumerate(pattern):
        for col,c in enumerate(line):
            if c=='1':
                p.append(f'<rect x="{x+col*unit:.1f}" y="{y+row*unit:.1f}" width="{unit-.6:.1f}" height="{unit-.6:.1f}" rx=".3" fill="{style}"/>')
    return ''.join(p)


def contribution_invaders(data, phase=0.0, *, write_file=True):
    """Large mobile-friendly arcade scene. Every GIF frame changes actors, shots and effects."""
    days=contribution_days(data)
    weeks=data.get('weeks',[])[-53:]
    total=int(data.get('totalContributions',0))
    active=sum(int(d.get('contributionCount',0))>0 for d in days)
    phase=phase%1
    b='''<defs>
        <radialGradient id="arcade-glow"><stop stop-color="#102c28"/><stop offset="1" stop-color="#060b10"/></radialGradient>
        <pattern id="scans2" width="4" height="4" patternUnits="userSpaceOnUse"><rect y="1" width="4" height="1" fill="#183e37" opacity=".18"/></pattern>
    </defs>'''
    b+='<rect x="18" y="14" width="1064" height="650" rx="20" fill="url(#arcade-glow)" stroke="#2b5351" stroke-width="2.5"/>'
    b+=tx(45,49,'SPACE INVADERS',36,'#73efaa',weight=700)
    b+=tx(45,79,'COMMIT DEFENSE // LIVE CONTRIBUTION ARCADE',18,'#8bbcae')
    b+=tx(1052,53,f'{total:06d}',32,'#f8f4da',weight=700,anchor='end')
    b+=tx(1052,81,'GITHUB SCORE',16,'#aabcc3',anchor='end')
    b+='<path d="M46 100H1052" stroke="#32645a" stroke-width="2"/>'
    # Readable 53-column grid with empty-day guides visible on mobile.
    for col,week in enumerate(weeks):
        for row,day in enumerate(week.get('contributionDays',[])):
            n=max(0,int(day.get('contributionCount',0)))
            color='#263a3b' if n==0 else '#2d8664' if n<=2 else '#44bc83' if n<=6 else '#69dfa1' if n<=12 else '#a3ffca'
            x=54+col*18.65; y=131+row*15.6
            b+=f'<rect x="{x:.1f}" y="{y:.1f}" width="13.7" height="11.3" rx="1.8" fill="{color}"/>'
    b+=tx(52,271,f'{active} ACTIVE DAYS  /  {len(weeks)} WEEKS OF REAL GITHUB ACTIVITY',18,'#8db8ac',weight=700)
    b+='<path d="M46 286H1052" stroke="#31514d" stroke-width="1.5"/>'
    # Large invading fleet, with authentic two-dimensional sprite art and motion in frame pixels.
    # This is a retro game animation, not claimed to be 3D.
    shift=36*math.sin(phase*math.tau)
    bob=8*math.sin(phase*2*math.tau)
    for row in range(2):
        for col in range(7):
            x=94+col*144+shift; y=326+row*94+bob
            if x<44 or x>1011: continue
            ink=('#52e8a0' if row==0 else '#76d9ff') if (col+row)%2==0 else '#43c98b'
            pat=ALIEN_A if (int(phase*16)%2) == (col%2) else ALIEN_B
            b+=alien_pixels(x,y,ink,7.0,pat)
    # stars twinkle and change actual pixel color/position each GIF frame
    for i in range(31):
        x=57+(i*173+21)%980; y=305+(i*53)%215
        lum=.22+.55*(.5+.5*math.sin(phase*math.tau*2+i*.81))
        b+=f'<circle cx="{x}" cy="{y}" r="{.9 if i%3 else 1.7}" fill="#d9ffe8" opacity="{lum:.2f}"/>'
    shipx=550+200*math.sin(phase*math.tau)
    # ship shadow, pixel player and 3 separate laser bullets at different phases
    b+=f'<ellipse cx="{shipx:.1f}" cy="600" rx="62" ry="8" fill="#0b241e"/>'
    b+=f'<path d="M{shipx:.1f} 547l-20 18h-19v16h-19v9h116v-9h-19v-16h-19Z" fill="#9cffe2" stroke="#225a53" stroke-width="3"/>'
    b+=f'<rect x="{shipx-10:.1f}" y="566" width="20" height="21" fill="#24a879"/>'
    for k in range(3):
        progress=(phase*2.3+k/3)%1
        ly=532-progress*198
        lx=shipx + 25*math.sin(k*3+phase*math.tau)
        b+=f'<rect x="{lx:.1f}" y="{ly:.1f}" width="6" height="26" rx="2" fill="#c6fff1"/>'
        b+=f'<rect x="{lx+1:.1f}" y="{ly-9:.1f}" width="4" height="8" fill="#49f7b3"/>'
    # visible motion trail and arcade atmosphere
    b+='<path d="M48 610H1052" stroke="#246b57" stroke-width="2" stroke-dasharray="11 8"/>'
    b+=tx(48,642,'PLAYER 01  //  JAY DONGA',17,'#8acbee',weight=700)
    b+=tx(1050,642,'LEVEL 53   |   3 LIVES   |   PRESS PLAY ONLINE',17,'#e3c68e',weight=700,anchor='end')
    b+='<rect x="18" y="14" width="1064" height="650" rx="20" fill="url(#scans2)" pointer-events="none"/>'
    doc=dark_shell(1100,681,b,'Large animated retro pixel arcade with verified GitHub heatmap')
    if write_file: write('invaders.svg',doc)
    return doc

def build_animated_gifs(data):
    """Render real motion into GIF pixels, including fonts and crisp alpha.

    SVG animation features alone do not animate under CairoSVG or all README
    renderers. Each frame is composed independently from the same real counts.
    """
    try:
        from io import BytesIO
        import cairosvg
        from PIL import Image
    except ImportError as exc:
        print('GIF dependencies missing; keeping static SVG:',str(exc))
        return
    for filename,func in [('isometric-calendar-v2.gif',contribution_isometric),('invaders-v2.gif',contribution_invaders)]:
        frames=[]
        count=20
        for idx in range(count):
            part=func(data,idx/count,write_file=False)
            if filename.startswith('isometric'):
                # A pale moving overhead sweep, placed only inside the stage.
                x=100+idx*42
                grad=f'<rect x="{x}" y="143" width="25" height="310" fill="#8affbf" opacity=".07"/>'
                part=part.replace('</svg>',grad+'</svg>')
            png=cairosvg.svg2png(bytestring=part.encode(),output_width=880,output_height=round(880*681/1100))
            im=Image.open(BytesIO(png)).convert('RGB')
            frames.append(im.quantize(colors=128,method=Image.Quantize.FASTOCTREE))
        # These names are distinct from v1 so GitHub's image cache does not keep old animations.
        dest=ASSETS/filename
        frames[0].save(dest,save_all=True,append_images=frames[1:],duration=110,loop=0,optimize=True,disposal=2)
        print('Rendered',filename,round(dest.stat().st_size/1024),'KiB',len(frames),'frames')

def identity():
    # Intentional initial-based pixel emblem, NOT a likeness or photo of the user.
    b='<defs><linearGradient id="badge" x2="1" y2="1"><stop stop-color="#44d6a3"/><stop offset="1" stop-color="#4daff2"/></linearGradient></defs>'
    b+='<circle cx="180" cy="178" r="130" fill="#112f37" stroke="#36766f" stroke-width="2"/>'
    for i in range(9):
        for j in range(9):
            distance=math.hypot(j-4,i-4)
            if 3.5<distance<4.5:
                b+=f'<circle cx="{104+j*19}" cy="{102+i*19}" r="3" fill="#54dfb8" opacity=".65"/>'
    b+=tx(180,209,'JD',98,'#69eac0',weight=800,anchor='middle',family='Arial,Helvetica,sans-serif')
    b+=tx(180,327,'JAY DONGA',18,'#9ecacb',weight=700,anchor='middle')
    write('identity.svg',svg(360,367,b,'Monogram of Jay Donga'))


def footer():
    b='<path d="M75 54h265M760 54h265" stroke="#315b5c" stroke-width="2"/>'
    b+=tx(550,60,'BUILD  /  LEARN  /  IMPROVE  /  REPEAT',19,'#75eac3',anchor='middle',weight=700)
    write('footer.svg',svg(1100,110,b,'Build learn improve repeat',rounded=16))


def initialize():
    focus_radar()
    identity()
    footer()
    stats(2,0,'—',verified=False)  # Snapshot of the two verified repos; followers unknown.
    languages({})
    empty_contribution_graphics()


def main():
    if '--init-offline' in sys.argv:
        initialize()
        return
    profile=get_json(f'https://api.github.com/users/{USERNAME}')
    repos=github_repos()
    stats(int(profile.get('public_repos',len(repos))),sum(int(x.get('stargazers_count',0)) for x in repos),int(profile.get('followers',0)),verified=True)
    lang={}
    for repo in repos:
        try:
            languages_data=get_json(f'https://api.github.com/repos/{USERNAME}/{repo["name"]}/languages')
            if isinstance(languages_data,dict):
                for name,value in languages_data.items():
                    if isinstance(value,(int,float)) and value>0:
                        lang[name]=lang.get(name,0)+value
        except (HTTPError,URLError,OSError,ValueError) as exc:
            print('Skipping language breakdown for',repo['name'],str(exc)[:120])
    if lang:
        languages(lang)
    else:
        print('Preserving previous language cards: no code bytes returned')
    focus_radar()
    identity()
    footer()
    contribution=contribution_info()
    if contribution:
        contribution_isometric(contribution)
        contribution_invaders(contribution)
        build_animated_gifs(contribution)
    else:
        print('Preserving existing contribution graphics (no synthetic contributions)')

if __name__=='__main__':
    main()