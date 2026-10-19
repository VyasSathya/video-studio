"""Use the existing studio.launch camera system for interface evidence films."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
from studio import launch,hf,media,music,verify
W=Path('C:/video-studio-work/runs/portfolio-landscape');C=W/'captures'
def plan(brief,beat):
    shots=[dict(kind='establish',start=0,end=2,beats=4,asset=brief['features'][0]['asset'],feature=0)];t=2
    for i,f in enumerate(brief['features']):
        shots.append(dict(kind='feature',start=t,end=t+3.5,beats=7,asset=f['asset'],feature=i));t+=3.5
    shots.append(dict(kind='end',start=t,end=t+4,beats=8,asset=None));return shots,t+4
def brief_for(id):
    if id=='marquee':
        features=[('A creative home.','marquee-hero.png',[200,500,2000,800]),('Stories in every frame.','marquee-work.png',[200,700,950,1050]),('The Marquee Studios.','spaces/marquee-gallery.png',[1040,400,1660,1190]),('The Loft Studios.','spaces/loft-gallery.png',[1040,400,1660,1190]),("Let's connect.",'marquee-contact.png',[900,400,1550,1200])]
        name='J Will Media';line="Website and workflows for John's studio.";sub='Website implementation by Vyas Sathya';accent='#c7b18e'
    else:
        features=[('A collection launch.','puzzle-hero.png',[250,300,2200,1300]),('The collection.','puzzle-hero.png',[1600,300,1000,1150]),('Connect wallet.','puzzle-hero.png',[270,780,1100,700]),('Art and code.','puzzle-team.png',[450,260,800,850])]
        name='Puzzle People';line='Historical collection launch.';sub='Art and code by Vyas Sathya';accent='#e8c64a'
    return dict(product=name,tokens=dict(bg='#101718' if id=='puzzle-people' else '#111214',fg='#f7f5f0',accent=accent,font='Geist',mono='Geist',radius=16,dim=86),features=[dict(title=t,asset=str(C/f),focus=focus,asset_size=[2880,1800]) for t,f,focus in features],end=dict(title=name,line=line,sub=sub),_sources=dict(captures='captures/sources.json',mode='Real captured interfaces; focus rectangles measured from the source images. No UI is redrawn.'))
def main():
    a=argparse.ArgumentParser();a.add_argument('--film',choices=['marquee','puzzle-people'],required=True);a.add_argument('--stills',action='store_true');args=a.parse_args()
    run=W/(args.film+'-launch');run.mkdir(exist_ok=True);b=brief_for(args.film)
    (run/'brief.json').write_text(json.dumps(b,indent=2),encoding='utf-8')
    old=launch.plan;launch.plan=plan
    shots,total=launch.build(b,run/'comp',1920,1080,.5);launch.plan=old
    # Preserve the photographed interface at its original brightness. The camera and
    # the separate title column provide focus without darkening surrounding controls.
    page=run/'comp/index.html';source=page.read_text(encoding='utf-8')
    source=source.replace('</style>','\n.spot{box-shadow:none!important}.h #win{-webkit-mask-image:none!important;mask-image:none!important}\n</style>')
    page.write_text(source,encoding='utf-8')
    sheet=verify.stills(run/'comp',shots,run/'stills',cols=4)
    m=dict(shots=shots,duration=total,end_t=shots[-1]['start'],holds=[[s['start']+1.3,s['end']] for s in shots if s['kind']=='feature']+[[shots[-1]['start'],total]],sources=[dict(source=f['asset'],sha256=hashlib.sha256(Path(f['asset']).read_bytes()).hexdigest()) for f in b['features']],producer='Existing video-studio studio.launch',width=1920,height=1080)
    (run/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
    if args.stills:return
    gates=verify.hf_check_json(run/'comp');(run/'gates.json').write_text(json.dumps(gates,indent=2),encoding='utf-8')
    hf.render(run/'comp',run/'silent.mp4',fps=30,quality='high',workers=2)
    music.launch_track(total,run/'score.wav',bpm=120,hit_at=m['end_t']);final=run/(args.film+'-launch-16x9.mp4')
    media.mux_loud(run/'silent.mp4',run/'score.wav',final,target=-14,peak=-1.5,crf=21)
    tech=verify.technical(final,m);(run/'technical.json').write_text(json.dumps(tech,indent=2),encoding='utf-8');verify.log(run,3,'render',tech)
    print(json.dumps(dict(final=str(final),technical=tech)))
if __name__=='__main__':main()
