"""Landscape Kpop Sing marketing film from the existing approved performance assets.

Uses the same local original score, real app capture, fonts and HyperFrames pipeline
as singstan-mv. It never presents a generated performer as a live app recording.
"""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0,str(HERE.parent/'singstan-mv'))
from studio import hf,media,verify
import track,cut
W=Path('C:/video-studio-work/runs/portfolio-landscape/kpop-sing-wide')
B=track.BEAT;D=track.SECONDS

def clip(source,out,offset,seconds,width,height):
    # Keep the faces in the top of the landscape crop. Center-cropping after
    # scaling would remove their heads. The legacy main wordmark is above y=200.
    vf=f'crop=720:1080:0:200,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(in_w-out_w)/2:0,setsar=1'
    subprocess.run([media.ffmpeg_bin(),'-y','-v','error','-ss',str(offset),'-i',str(source),'-t',str(seconds),'-vf',vf,'-r','30','-an','-c:v','libx264','-crf','17','-pix_fmt','yuv420p',str(out)],check=True)

def build():
    comp=W/'comp';comp.mkdir(parents=True,exist_ok=True)
    font=Path('C:/video-studio-work/runs/singstan-mv/npm/node_modules/@fontsource/anton/files/anton-latin-400-normal.woff2')
    shutil.copyfile(font,comp/'anton.woff2');shutil.copyfile(cut.SCREEN,comp/'home.png');shutil.copyfile(cut.ICON,comp/'icon.png')
    sources=[]
    specs=[('opening','L',.4,4*B,1080,1080),('second','G',1.2,4*B,1080,1080),('duet-l','L',.6,4*B,760,1080),('duet-g','G',1.4,4*B,760,1080),('last-l','L',2.3,3*B,1080,1080),('last-g','G',2.7,3*B,1080,1080)]
    for name,key,offset,seconds,width,height in specs:
        source=cut.SRC[key];out=comp/(name+'.mp4')
        clip(source,out,offset,seconds,width,height)
        sources.append(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output=out.name,offset=offset,seconds=seconds,crop=[0,200,720,1080],anchor='top after aspect-preserving scale',producer='Previously approved Fal Seedance performance; reused without new generation'))
    def video(name,start,duration,cls,idx):return f'<video id="performance-{name}" class="{cls}" src="{name}.mp4" data-start="{start}" data-duration="{duration}" data-track-index="{idx}" muted playsinline></video>'
    layers=[];anims=[];shots=[]
    def section(id,b0,b1,body):
        start=round(b0*B,6);end=round(b1*B,6);layers.append(f'<section id="{id}" class="scene">{body}</section>');shots.append(dict(kind='feature' if id!='end' else 'end',start=start,end=end))
        anims.append(f"tl.set('#{id}',{{visibility:'visible'}},{start});tl.fromTo('#{id} .type',{{y:25,opacity:0}},{{y:0,opacity:1,duration:.25,ease:'power3.out',immediateRender:false}},{start});tl.set('#{id}',{{visibility:'hidden'}},{end});")
    small='<p class="brand">KPOP SING / K-POP KARAOKE</p>'
    section('one',0,4,video('opening',0,4*B,'performance',1)+small+'<div class="type"><h1>SING<br>K-POP.</h1></div>')
    section('two',4,8,video('second',4*B,4*B,'performance',2)+small+'<div class="type"><h1>WITHOUT<br>READING<br>KOREAN.</h1></div>')
    section('duet',8,12,video('duet-l',8*B,4*B,'duet left',3)+video('duet-g',8*B,4*B,'duet right',4)+small+'<div class="type"><h1>LYRICS<br>SPELLED<br>HOW THEY<br>SOUND.</h1></div>')
    section('app',12,20,small+'<div class="type"><h1>PICK<br>A SONG.</h1><p class="fine">From the real app.</p></div><div class="catalog"><img src="home.png" alt="Kpop Sing song catalog" data-layout-allow-overflow></div>')
    section('lastone',20,23,video('last-l',20*B,3*B,'performance',5)+small+'<div class="type"><h1>YOUR TURN<br>ON THE<br>MIC.</h1></div>')
    section('lasttwo',23,26,video('last-g',23*B,3*B,'performance',6)+small+'<div class="type"><h1>YOUR TURN<br>ON THE<br>MIC.</h1></div>')
    section('end',26,32,'<img class="icon" src="icon.png" alt=""><div class="type"><p class="kind">K-POP KARAOKE</p><h1>KPOP SING</h1><p class="tagline">YOUR K-POP PRACTICE ROOM.</p></div>')
    css="""@font-face{font-family:Anton;src:url('anton.woff2')}*{box-sizing:border-box;margin:0}html,body,#root{width:1920px;height:1080px;overflow:hidden;background:#14071f;color:#fff7fb;font-family:Anton,Arial,sans-serif}.scene{position:absolute;inset:0;visibility:hidden;overflow:hidden;background:#14071f}.performance{position:absolute;left:840px;top:0;width:1080px;height:1080px;object-fit:cover}.brand{position:absolute;left:80px;top:60px;font-size:25px;letter-spacing:.08em;color:#ff78c0}.type{position:absolute;left:80px;top:270px;opacity:0}h1{font-weight:400;font-size:146px;line-height:1.05;letter-spacing:-.015em}.duet{position:absolute;top:0;width:760px;height:1080px;object-fit:cover}.duet.left{left:400px}.duet.right{left:1160px;border-left:6px solid #ff2e9a}#duet .type{left:55px;top:410px}#duet h1{font-size:100px}#duet .brand{left:55px;font-size:21px;max-width:300px}#app{background:#ff2e9a;color:#14071f}#app .brand{color:#14071f}#app .type{top:290px}#app h1{font-size:150px}.fine{font-size:30px;letter-spacing:.02em;margin-top:30px}.catalog{position:absolute;left:860px;top:70px;width:980px;height:940px;overflow:hidden;border-radius:24px;box-shadow:0 30px 90px #14071f55}.catalog img{position:absolute;left:0;top:-660px;width:980px;height:auto}#end{background:#ff2e9a;color:#14071f;display:flex;align-items:center;justify-content:center;gap:90px}#end .icon{width:370px;height:370px;border-radius:76px}#end .type{position:static}#end h1{font-size:180px;white-space:nowrap}#end .kind{font-size:31px;letter-spacing:.12em;margin-bottom:12px}#end .tagline{font-size:42px;margin-top:22px}"""
    page=f'''<!doctype html><html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{css}</style></head><body><div id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="{D}">{''.join(layers)}</div><script>const tl=gsap.timeline({{paused:true}});{''.join(anims)}window.__timelines={{main:tl}};</script></body></html>'''
    (comp/'index.html').write_text(page,encoding='utf-8')
    manifest=dict(duration=D,width=1920,height=1080,end_t=26*B,holds=[[12*B,20*B],[26*B,D]],hold_reason='The real catalog screenshot and closing identity are deliberate reading holds. Performance clips have no hold exemptions.',sources=sources,screen=dict(source=str(cut.SCREEN),sha256=hashlib.sha256(cut.SCREEN.read_bytes()).hexdigest()),audio='singstan-mv/track.py original local dance-pop score, no commercial recording or lyrics',claims='Marketing composition. Generated performance footage is not live karaoke playback or device QA.',shots=shots)
    (W/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');return comp,manifest

def main():
    a=argparse.ArgumentParser();a.add_argument('--stills',action='store_true');args=a.parse_args()
    comp,m=build();times=[.8,2.8,4.7,6.7,8.6,10.3,11.7,13.2,14.7]
    verify.stills(comp,[],W/'stills',cols=3,times=times)
    if args.stills:return
    gates=verify.hf_check_json(comp);(W/'gates.json').write_text(json.dumps(gates,indent=2))
    if not gates['ok']:raise RuntimeError('Composition checks failed; inspect gates.json before rendering.')
    hf.render(comp,W/'silent.mp4',fps=30,quality='high',workers=2)
    track.main(W/'score.wav');final=W/'kpop-sing-wide-16x9.mp4';media.mux_loud(W/'silent.mp4',W/'score.wav',final,target=-14,peak=-1.5,crf=20)
    tech=verify.technical(final,m);(W/'technical.json').write_text(json.dumps(tech,indent=2));frames=media.frames(final,W/'frames',times);verify.tile(frames,W/'strip.png',cols=3,labels=[str(t) for t in times]);verify.log(W,4,'render',tech);print(json.dumps(tech))
if __name__=='__main__':main()
