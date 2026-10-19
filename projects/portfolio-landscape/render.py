"""Landscape composition using the existing video-studio runtime; no paid adapters."""
import argparse,hashlib,html,json,os,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from studio import hf,launch,media,music,verify
WORK=Path(os.environ.get('PORTFOLIO_FILM_WORK','C:/video-studio-work/runs/portfolio-landscape'))
esc=lambda s:html.escape(str(s),quote=True)

CSS='''*{margin:0;box-sizing:border-box}html,body,#root{width:1920px;height:1080px;overflow:hidden}body{font-family:Geist,Arial,sans-serif;color:#f4f3f0;background:#111214}#root{position:relative}.shot{position:absolute;inset:0;visibility:hidden;overflow:hidden;background:#111214}.picture{position:absolute;inset:0}.picture img,.picture video{width:100%;height:100%;object-fit:cover}.copy{position:absolute;left:110px;bottom:95px;width:740px;opacity:0}.product{font-size:24px;letter-spacing:.025em;margin-bottom:20px;color:var(--brand)}h1{font-size:72px;line-height:1.04;letter-spacing:-.045em;font-weight:500;max-width:850px}.sub{font-size:24px;line-height:1.45;color:#b9babf;margin-top:23px;max-width:650px}.wide .copy{background:linear-gradient(90deg,#111214ef,#111214d9 78%,transparent);left:0;bottom:0;padding:75px 100px 75px 110px;width:100%;height:340px}.wide .copy h1{font-size:58px}.wide .sub{margin-top:12px}.screen .picture{inset:80px 80px 80px 600px;border:1px solid #ffffff2b;border-radius:18px;overflow:hidden;box-shadow:0 40px 100px #0007}.screen .picture img{object-fit:contain;background:#151719}.screen .copy{left:90px;top:350px;width:440px}.screen h1{font-size:66px}.phone .picture{left:1120px;top:65px;width:425px;height:950px;border:1px solid #ffffff30;border-radius:40px;overflow:visible;box-shadow:0 30px 100px #0009}.phone .picture img{border-radius:40px;object-fit:cover;object-position:top}.phone .picture .second{position:absolute;width:340px;height:740px;left:290px;top:140px;opacity:.7;z-index:-1}.phone .copy{top:340px;bottom:auto;width:850px}.phone h1{font-size:94px}.phone .sub{font-size:28px;max-width:730px}.art .picture{left:800px;right:40px;top:80px;bottom:80px}.art .picture img{object-fit:contain}.art .copy{bottom:240px;width:620px}.art h1{font-size:84px}#end{position:absolute;inset:0;visibility:hidden;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#111214}#end h2{font-size:104px;letter-spacing:-.055em;font-weight:500;opacity:0}#end p{font-size:29px;color:#bbbcc0;margin-top:26px;opacity:0}#end span{font-size:21px;color:#9aa3a7;margin-top:40px;opacity:0}'''

def build(film):
    run=WORK/film['id'];comp=run/'comp';comp.mkdir(parents=True,exist_ok=True)
    fonts=launch.font_faces(['Geist'],comp);layers=[];anim=[];t=0;receipts=[];track=1;holds=[]
    for i,shot in enumerate(film['shots']):
        src=Path(shot['source']);name=f'asset-{i}{src.suffix}';shutil.copyfile(src,comp/name)
        dur=shot.get('duration',4);start=round(t,3);end=round(t+dur,3)
        receipts.append(dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),start=shot.get('offset',0),duration=dur,provenance=shot['provenance']))
        if src.suffix.lower() in ('.mp4','.webm'):
            content=f'<video id="v{i}" src="{name}" data-start="{start}" data-duration="{dur}" data-track-index="{track}" data-media-start="{shot.get("offset",0)}" muted playsinline></video>';track+=1
        else:content=f'<img src="{name}" alt="">'
        if shot.get('second'):
            p=Path(shot['second']);n=f'second-{i}{p.suffix}';shutil.copyfile(p,comp/n);content+=f'<img class="second" src="{n}" alt="">'
            receipts.append(dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),provenance=shot['provenance']))
        mode=shot.get('layout','wide')
        layers.append(f'<section class="shot {mode}" id="s{i}" style="--brand:{shot.get("accent",film["accent"])}"><div class="picture">{content}</div><div class="copy"><p class="product">{esc(shot.get("label",film["name"]))}</p><h1>{esc(shot.get("title",""))}</h1><p class="sub">{esc(shot.get("sub",""))}</p></div></section>')
        camera_d=min(1.7,dur*.45)
        anim.append(f"tl.set('#s{i}',{{visibility:'visible'}},{start});tl.fromTo('#s{i} .picture',{{scale:1.07,y:20,rotationY:-3,rotationX:2,transformPerspective:1800}},{{scale:1,y:0,rotationY:0,rotationX:0,duration:{camera_d},ease:'power3.out',immediateRender:false}},{start});tl.fromTo('#s{i} .copy',{{opacity:0,y:20}},{{opacity:1,y:0,duration:.65,ease:'power3.out',immediateRender:false}},{start+.18});tl.set('#s{i}',{{visibility:'hidden'}},{end});")
        if src.suffix.lower() not in ('.mp4','.webm'):
            # The final eased pixels are visually still; only still-image shots may declare this hold.
            holds.append([round(start+max(0,camera_d-.9),3),end])
        for a,b in shot.get('source_reading_holds',[]):holds.append([start+a,start+b])
        t=end
    end_t=t;total=t+3.5
    layers.append(f'<section id="end"><h2>{esc(film["name"])}</h2><p>{esc(film["line"])}</p><span>{esc(film.get("end","Vyas Sathya"))}</span></section>')
    anim.append(f"tl.set('#end',{{visibility:'visible'}},{end_t});tl.fromTo('#end h2',{{opacity:0,y:16}},{{opacity:1,y:0,duration:.6,immediateRender:false}},{end_t});tl.fromTo('#end p,#end span',{{opacity:0}},{{opacity:1,duration:.7,immediateRender:false}},{end_t+.35});")
    extra='.phone-focus .picture{left:1000px;right:80px;top:130px;bottom:130px;overflow:hidden;border-radius:28px;border:1px solid #ffffff30}.phone-focus img{object-position:top}.phone-focus .copy{top:330px;bottom:auto;width:800px}.phone-focus h1{font-size:94px}.phone,.phone-focus{background:radial-gradient(ellipse at 75% 50%,#42253855,transparent 65%),#111214}'
    extra+='.comparison .picture{inset:25px 80px 190px}.comparison .picture img{object-fit:contain}.comparison .copy{left:110px;bottom:30px;width:1700px}.comparison .product{display:none}.comparison h1{font-size:48px}.comparison .sub{font-size:21px;margin-top:8px}'
    extra+='.art .picture video{object-fit:cover}.excerpt .copy{left:auto;right:45px;top:36px;bottom:auto;width:auto;max-width:700px;background:#111214e8;border:1px solid #ffffff30;border-radius:10px;padding:16px 24px}.excerpt .product,.excerpt .sub{display:none}.excerpt h1{font-size:28px;letter-spacing:-.025em}.excerpt .picture video{object-fit:contain;background:#111214}'
    extra+='.game .picture{inset:45px 45px 45px 650px;border-radius:18px;overflow:hidden;border:1px solid #ffffff25}.game .picture video{object-fit:cover}.game .copy{left:80px;top:340px;bottom:auto;width:500px}.game h1{font-size:76px}.game .sub{font-size:24px}.game .product{font-size:24px}'
    extra+='.clean .copy{display:none}.proof .picture{inset:60px 60px 60px 650px;overflow:hidden;border-radius:16px}.proof .picture img{object-fit:contain}.proof .copy{left:85px;top:360px;bottom:auto;width:510px}.proof h1{font-size:70px}'
    css=CSS.replace('z-index:-1','z-index:0')
    if film.get('bg'):
        extra+=f".shot,#end{{background:{film['bg']};color:{film.get('fg','#f4f3f0')}}}.sub,#end p{{color:{film.get('muted','#aeb4b2')}}}"
    fonts+=launch.font_faces(film.get('fonts',[]),comp)
    extra+=film.get('css','')
    page=f'''<!doctype html><html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{fonts}{css}{extra}</style></head><body><div id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="{total}">{''.join(layers)}</div><script>const tl=gsap.timeline({{paused:true}});{''.join(anim)}window.__timelines=window.__timelines||{{}};window.__timelines.main=tl;</script></body></html>'''
    (comp/'index.html').write_text(page,encoding='utf-8')
    m=dict(id=film['id'],width=1920,height=1080,duration=total,end_t=end_t,holds=holds+[[end_t,total]],hold_reason='Camera settles, then the original screen holds for reading. End card holds deliberately.',inputs=receipts,shots=film['shots'],audio='Original local studio.music score; no speech',tool='video-studio HyperFrames')
    (run/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
    return run,comp,m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--film',required=True);ap.add_argument('--stills',action='store_true');ap.add_argument('--build',action='store_true');a=ap.parse_args()
    config=WORK/'films.json'
    if not config.exists():config=HERE/'production-plan.json'
    films=json.loads(config.read_text(encoding='utf-8'));film=next(f for f in films if f['id']==a.film)
    run,comp,m=build(film)
    if a.build:return
    ts=[];t=0
    for s in film['shots']:ts.extend([t+.5,t+s.get('duration',4)-.5]);t+=s.get('duration',4)
    ts.append(m['duration']-1)
    sheet=verify.stills(comp,[],run/'stills',times=ts,cols=3)
    blanks=verify.blank_frames(sorted((run/'stills').glob('frame-*.png')))
    (run/'stills-check.json').write_text(json.dumps(dict(sheet=str(sheet),blank=blanks),indent=2),encoding='utf-8')
    if a.stills:return
    gates=verify.hf_check_json(comp);(run/'hyperframes-check.json').write_text(json.dumps(gates,indent=2),encoding='utf-8')
    if not gates.get('ok'):raise RuntimeError('HyperFrames preflight failed; render withheld')
    hf.render(comp,run/'silent.mp4',fps=30,quality='high',workers=2)
    music.launch_track(m['duration'],run/'score.wav',bpm=100,hit_at=m['end_t'],seed=film.get('seed',3))
    final=run/(film['id']+'-16x9.mp4');media.mux_loud(run/'silent.mp4',run/'score.wav',final,target=-14,peak=-1.5,crf=21)
    tech=verify.technical(final,m);(run/'technical.json').write_text(json.dumps(tech,indent=2),encoding='utf-8')
    frames=media.frames(final,run/'frames',ts);verify.tile(frames,run/'strip.png',cols=3,width=640,labels=[str(t) for t in ts]);verify.log(run,1,'render',tech)
    print(json.dumps(dict(final=str(final),technical=tech)))
if __name__=='__main__':main()
