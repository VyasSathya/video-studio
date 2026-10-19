"""Readable portfolio overview from real, reviewed landscape films.

All sixteen selected cases; source picture only, with no performance speech edits.
"""
import hashlib,json,subprocess,sys,os,runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
from studio import media,music,verify
score_overview=runpy.run_path(str(HERE/'score-overview.py'))['score']
from fontTools.ttLib import TTFont
BASE=Path('C:/video-studio-work/runs/portfolio-landscape')
RUN=BASE/'overview-all16';SITE=Path(os.environ.get('PORTFOLIO_SITE_ROOT','C:/Dev/VyasSathya.github.io'))
PLAN=[('Talkover','talkover.mp4',2,6),('Kpop Sing','kpop-sing.mp4',.8,6),('Brainrot Brawl','brainrot-brawl.mp4',0,6),('Punchpad','punchpad.mp4',3,6),('crewboard','crewboard.mp4',4,6),('agent-brain','agent-brain.mp4',14,6),('J Will Media / Marquee','marquee.mp4',3.2,6),('Front of Line','front-of-line.mp4',2,6),('Flower Girls','flower-girls.mp4',3.5,6),('Puzzle People','puzzle-people.mp4',3,6),('Stand-up / Vyas Sathya','standup-highlights.mp4',13,5.5),('Whiteboard films','range-whiteboard.mp4',15,6),('video-studio','video-studio.mp4',0,7),('Mad Balls','mad-balls.mp4',0,9.4),('BuildWhatever','buildwhatever.mp4',2.5,6),('3D asset pipeline','asset-pipeline.mp4',2,6)]
def run(a):subprocess.run([str(x) for x in a],cwd=RUN,check=True)
def main():
    RUN.mkdir(parents=True,exist_ok=True);font=TTFont(SITE/'fonts/geist-latin-500-normal.woff2');font.flavor=None;font.save(RUN/'geist.ttf');receipts=[];t=0;holds=[]
    for i,(name,file,start,duration) in enumerate(PLAN):
        source=SITE/'media'/file;target=RUN/f'clip-{i:02d}.mp4'
        y=984 if file in ['agent-brain.mp4','buildwhatever.mp4','flower-girls.mp4'] else 28
        x=30 if file in ['buildwhatever.mp4','flower-girls.mp4'] else 1390
        label='Kpop Sing / Marketing' if file=='kpop-sing.mp4' else 'BuildWhatever / Source' if file=='buildwhatever.mp4' else 'Mad Balls / inside Brainrot Brawl' if file=='mad-balls.mp4' else name
        label_size=28 if file=='mad-balls.mp4' else 36
        vf=f"scale=1920:1080:flags=lanczos,setsar=1,drawbox=x={x}:y={y}:w=500:h=66:color=black@0.85:t=fill,drawtext=fontfile=geist.ttf:text='{label}':fontcolor=white:fontsize={label_size}:x={x+18}:y={y+11}"
        cached='--resume' in sys.argv and target.exists() and abs(media.duration(target)-duration)<.05
        if file=='video-studio.mp4':
            # The tool is introduced by the input artifact, then its distinct whiteboard output.
            vf=f"[0:v]trim=start=0:duration=3,setpts=PTS-STARTPTS[a];[0:v]trim=start=9:duration=4,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0,{vf}[out]"
            run([media.ffmpeg_bin(),'-y','-v','error','-i',source,'-filter_complex',vf,'-map','[out]','-an','-r',30,'-c:v','libx264','-crf',19,'-preset','fast','-pix_fmt','yuv420p',target])
        elif not cached or file=='flower-girls.mp4':run([media.ffmpeg_bin(),'-y','-v','error','-ss',start,'-t',duration,'-i',source,'-an','-vf',vf,'-r',30,'-c:v','libx264','-crf',19,'-preset','fast','-pix_fmt','yuv420p',target])
        receipts.append(dict(project=name,source_file=file,source_start=start,duration=duration,timeline_start=t,source_ranges=[[0,3],[9,13]] if file=='video-studio.mp4' else [[start,start+duration]],sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        # Inherit only the exact inspected reading holds from accepted source manifests.
        source_id={'standup-highlights':'standup','range-whiteboard':'whiteboard'}.get(source.stem,source.stem)
        source_manifest=BASE/source_id/'manifest.json'
        if file=='video-studio.mp4':holds.extend([[t+.45,t+3],[t+4.3,t+7]])
        elif source_manifest.exists():
            for a,b in json.loads(source_manifest.read_text()).get('holds',[]):
                a,b=max(start,a),min(start+duration,b)
                if a<b:holds.append([round(t+a-start,4),round(t+b-start,4)])
        if file=='asset-pipeline.mp4':holds.append([t,t+2])
        if file=='range-whiteboard.mp4':holds.append([t+4,t+duration])
        t+=duration
    end=RUN/'end.mp4';vf="drawtext=fontfile=geist.ttf:text='Vyas Sathya':fontcolor=white:fontsize=104:x=(w-tw)/2:y=430,drawtext=fontfile=geist.ttf:text='From idea to working product.':fontcolor=0xaaaaaa:fontsize=36:x=(w-tw)/2:y=570"
    run([media.ffmpeg_bin(),'-y','-v','error','-f','lavfi','-i','color=c=0x111214:s=1920x1080:r=30:d=3.5','-vf',vf,'-an','-c:v','libx264','-crf',19,'-preset','fast','-pix_fmt','yuv420p',end])
    (RUN/'concat.txt').write_text(''.join(f"file 'clip-{i:02d}.mp4'\n" for i in range(len(PLAN)))+"file 'end.mp4'\n",encoding='utf-8')
    run([media.ffmpeg_bin(),'-y','-v','error','-f','concat','-safe','0','-i',RUN/'concat.txt','-c','copy',RUN/'silent.mp4'])
    score_overview(t+3.5,RUN/'score.wav')
    final=RUN/'portfolio-overview-16x9.mp4';media.mux_loud(RUN/'silent.mp4',RUN/'score.wav',final,target=-14,peak=-3,crf=20)
    m=dict(width=1920,height=1080,duration=t+3.5,shots=receipts,holds=holds+[[t,t+3.5]],audio='Original locally synthesized electric-piano score, projects/portfolio-landscape/score-overview.py. Every source film is picture only; no stand-up speech, punchline audio or audience sound is chopped into the montage. Full uninterrupted performance reel remains separate.',tool='Existing video-studio ffmpeg, music and verify modules.',coverage='All sixteen selected cases. Kpop is generated marketing footage, gameplay is an existing bot development capture, BuildWhatever is historical public-source architecture. No runtime or outcome claims added.')
    (RUN/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');tech=verify.technical(final,m);(RUN/'technical.json').write_text(json.dumps(tech,indent=2));verify.log(RUN,1,'technical',tech)
    times=[s['timeline_start']+x for s in receipts for x in [.6,min(4.8,s['duration']-.5)]]+[t+2]
    frames=media.frames(final,RUN/'frames',times);verify.tile(frames,RUN/'strip.png',cols=3,width=640,labels=[str(round(x,1))+'s' for x in times]);print(json.dumps(tech))
if __name__=='__main__':main()
