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


def contribution_isometric(data,phase=0.0,*,write_file=True):
    """52/53 x 7 isometric terrain, anchored to *verified* GraphQL calendar days."""
    weeks=data.get('weeks',[])[-53:]
    days=contribution_days(data)
    cur,longest,high,avg=streak_metrics(days)
    total=int(data.get('totalContributions',0))
    b="""<defs>
      <linearGradient id="iso-floor" x2="0" y2="1"><stop stop-color="#0c1519"/><stop offset="1" stop-color="#101a21"/></linearGradient>
      <linearGradient id="iso-glow" x2="1" y2="0"><stop stop-color="#34df8e" stop-opacity="0"/><stop offset=".5" stop-color="#36e9a0" stop-opacity=".17"/><stop offset="1" stop-color="#34df8e" stop-opacity="0"/></linearGradient>
      <style>@media (prefers-reduced-motion: reduce) { .voxel animate { display:none; } }</style>
    </defs>"""
    b+=f'<rect x="35" y="105" width="764" height="305" rx="12" fill="url(#iso-floor)"/>'
    b+=tx(41,51,'CONTRIBUTIONS CALENDAR',27,'#70caff',weight=700)
    b+=tx(1056,51,'GITHUB  /  53-WEEK VIEW',15,'#82a5b3',anchor='end')
    b+='<path d="M42 69H1058" stroke="#273740" stroke-width="1.4"/>'
    b+=tx(64,128,'REAL CONTRIBUTION ACTIVITY  ·  HEIGHT = CONTRIBUTIONS',12,'#547d7d')
    # Sort back-to-front so neighboring days naturally occlude each other.
    render=[]
    for col,week in enumerate(weeks):
        for row,day in enumerate(week.get('contributionDays',[])):
            count=max(0,int(day.get('contributionCount',0)))
            x=71+col*12.15+row*10.1
            y=183+col*3.52-row*5.15
            h=2 if count==0 else min(50,4+round(6.2*math.sqrt(count)))
            color=('#18242a','#14232a','#122126') if count==0 else (('#175c41','#115037','#0d322b') if count<=2 else ('#238d58','#1a6746','#124634') if count<=6 else ('#39bd79','#218a5a','#15583a') if count<=12 else ('#53ec93','#2a9d65','#176442'))
            render.append((col+row,voxel(x,y,h,*color,day.get('date',''),count)))
    for _,piece in sorted(render,key=lambda e:e[0]):
        b+=piece
    b+=f'<rect x="46" y="378" width="5" height="10" rx="2" fill="#3ee69c" opacity=".55"/>'
    b+=tx(61,388,f'{total} CONTRIBUTIONS REPORTED',13,'#71c6ac',weight=700)
    b+=tx(778,388,'LATEST YEAR',12,'#6b9c9e',anchor='end')
    # Right-side metrics arranged to echo the supplied visual reference.
    b+='<path d="M821 110V405" stroke="#2c393e" stroke-width="1.1"/>'
    b+=tx(850,132,'COMMIT STREAKS',21,'#71bdf2',weight=700)
    b+=tx(851,171,f'Current streak  {cur} day'+('' if cur==1 else 's'),18,'#cad6db')
    b+=tx(851,204,f'Best streak     {longest} days',18,'#cad6db')
    b+='<path d="M851 227H1045" stroke="#263b43"/>'
    b+=tx(850,261,'CONTRIBUTIONS / DAY',21,'#71bdf2',weight=700)
    b+=tx(851,300,f'Highest in a day   {high}',18,'#cad6db')
    b+=tx(851,332,f'Average per day    {avg:.2f}',18,'#cad6db')
    b+=tx(851,386,'DAILY DATA FROM GITHUB',12,'#578f7d',weight=700)
    b+=tx(1055,432,'JAY DONGA   •   @jd2009-k',13,'#547d82',anchor='end')
    doc=dark_shell(1100,455,b,'Animated isometric contribution calendar for Jay Donga')
    if write_file:
        write('isometric-calendar.svg',doc)
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


def contribution_invaders(data,phase=0.0,*,write_file=True):
    days=contribution_days(data)
    weeks=data.get('weeks',[])[-53:]
    total=int(data.get('totalContributions',0))
    b="""<defs>
     <pattern id="scans" width="4" height="4" patternUnits="userSpaceOnUse"><rect y="1" width="4" height="1" fill="#0c2a22" opacity=".22"/></pattern>
     <filter id="neon"><feGaussianBlur stdDeviation="1.7"/></filter>
     <style>@media (prefers-reduced-motion: reduce) { animate, animateTransform { display:none; } }</style>
    </defs>"""
    b+='<rect x="21" y="16" width="1058" height="397" rx="14" fill="#05090d" stroke="#21363e" stroke-width="2"/>'
    b+=tx(43,42,'1UP',15,'#f4a6a6',weight=700)
    b+=tx(43,64,f'{total:06d}',19,'#f0f5f3',weight=700)
    b+=tx(237,42,'HIGH SCORE',15,'#f1a6a6',weight=700)
    b+=tx(237,64,f'{total:06d}',19,'#f5faf7',weight=700)
    b+=tx(550,47,'SPACE INVADERS  //  COMMIT DEFENSE',19,'#4beb8f',weight=700,anchor='middle')
    b+=tx(831,42,'STAGE',15,'#f1a6a6',weight=700)
    b+=tx(831,64,f'{len(weeks)} WEEKS',16,'#f1f5f5',weight=700)
    b+=tx(981,42,'SHIPS',15,'#f1a6a6',weight=700)
    for k in range(3):
        b+=f'<polygon points="{977+k*23},57 {986+k*23},46 {996+k*23},57" fill="#48dba3"/>'
    b+='<path d="M43 77H1057" stroke="#2b4647" stroke-width="1.2"/>'
    # Real contribution heatmap as the arcade invasion ceiling. 53 columns x 7 rows.
    for col,week in enumerate(weeks):
        for row,day in enumerate(week.get('contributionDays',[])):
            n=max(0,int(day.get('contributionCount',0)))
            color='#111c23' if not n else '#205e45' if n<=2 else '#2d9461' if n<=6 else '#53d48b' if n<=12 else '#77f9a4'
            x=65+col*18.1;y=96+row*12.0
            b+=f'<rect x="{x:.1f}" y="{y:.1f}" width="12" height="9" rx="1.1" fill="{color}"/>'
    b+=tx(54,190,'LIVE ACTIVITY GRID  /  {0} CONTRIBUTION DAYS'.format(sum(int(d.get('contributionCount',0))>0 for d in days)),12,'#446d59')
    # Small starfield behind the invaders. Twinkles use SVG animation plus GIF-frame variant.
    for i in range(27):
        x=60+(i*151+37)%967;y=210+(i*59)%119
        opacity=.20+.2*((i+int(phase*7))%3)
        b+=f'<circle cx="{x}" cy="{y}" r="{.7 if i%4 else 1.3}" fill="#d1e5d6" opacity="{opacity:.2f}"><animate attributeName="opacity" values=".15;.70;.15" dur="{2+i%6}s" begin="-{i%4}s" repeatCount="indefinite"/></circle>'
    # 8-bit characters march left-right, matching the supplied screenshot but original art.
    off=math.sin(phase*math.tau)*12.5
    b+=f'<g transform="translate({off:.1f} 0)">'
    b+='<animateTransform attributeName="transform" type="translate" values="-12 0;12 0;-12 0" dur="3.5s" repeatCount="indefinite"/>'
    lastdays=days[-35:]
    alive=[d for d in lastdays if int(d.get('contributionCount',0))>0]
    # Arcade ships remain decorative even with zero contributions; strong color reflects verified activity.
    chosen=sorted(alive,key=lambda d:int(d.get('contributionCount',0)),reverse=True)[:6]
    for i in range(6):
        n=int(chosen[i]['contributionCount']) if i<len(chosen) else 0
        x=205+i*130;y=236+(i%2)*12
        color='#29644b' if n==0 else '#3bc07a' if n<=5 else '#65f6a2'
        b+=alien_pixels(x,y,color,4.9,ALIEN_A if i%2 else ALIEN_B)
    b+='</g>'
    # Laser / ship with animation: fallback frame values are baked into animated GIF.
    laser_y=321-(phase%1.0)*103
    b+=f'<rect x="551" y="{laser_y:.1f}" width="3" height="19" rx="1" fill="#a9ffcf">'
    b+='<animate attributeName="y" values="321;207" dur="1.4s" repeatCount="indefinite"/></rect>'
    b+='<path d="M551 316l-7 10h-9v8h-10v5h52v-5h-10v-8h-9Z" fill="#66efad"/>'
    b+='<rect x="547" y="323" width="9" height="15" fill="#1f8d66"/>'
    b+='<path d="M45 353H1055" stroke="#194737" stroke-dasharray="7 6" stroke-width="1.5"/>'
    b+=tx(44,384,'PLAYER: JAY DONGA',13,'#77aedc',weight=700)
    b+=tx(547,384,f'YEARLY CONTRIBUTIONS: {total}',13,'#83b49f',weight=700,anchor='middle')
    b+=tx(1050,384,'CREDIT 01  /  REAL DATA',13,'#d0a871',weight=700,anchor='end')
    b+='<rect x="20" y="18" width="1060" height="393" fill="url(#scans)" pointer-events="none"/>'
    doc=dark_shell(1100,432,b,'Animated Space Invaders arcade built from Jay Donga contribution data',radius=18)
    if write_file:
        write('invaders.svg',doc)
    return doc


def build_animated_gifs(data):
    """GitHub embeds GIF in README reliably; animated SVG may be cached/sanitized.

    GitHub Actions installs Pillow and CairoSVG before calling this function.
    GIFs contain real data and are built by re-rendering 12 deterministic phases.
    No remote animation service, secrets or fake numbers.
    """
    try:
        from io import BytesIO
        import cairosvg
        from PIL import Image
    except ImportError as exc:
        print('Optional GIF dependency unavailable; publishing animated SVG only:',str(exc))
        return
    for filename,func in [('isometric-calendar.gif',contribution_isometric),('invaders.gif',contribution_invaders)]:
        imgs=[]
        count=12
        for idx in range(count):
            frame=func(data,idx/count,write_file=False)
            # For iso animate a scanning highlight without falsifying any cell data.
            if filename.startswith('isometric'):
                x=70+idx*57
                overlay=f'<rect x="{x}" y="140" width="20" height="245" fill="#3ee69c" opacity=".02"/>'
                frame=frame.replace('</svg>',overlay+'</svg>')
            im=Image.open(BytesIO(cairosvg.svg2png(bytestring=frame.encode(),output_width=880,output_height=round((455 if filename.startswith('isometric') else 432)*.8))))
            imgs.append(im.convert('RGB').quantize(colors=80,method=Image.Quantize.FASTOCTREE))
        dest=ASSETS/filename
        imgs[0].save(dest,save_all=True,append_images=imgs[1:],duration=140,loop=0,optimize=True,disposal=2)
        print('Rendered',filename,round(dest.stat().st_size/1024),'KiB')


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