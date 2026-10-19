"""Readable portfolio overview from real, reviewed landscape films.

Six seconds per product; no portrait canvas or interior joke edits.
"""
import hashlib,json,subprocess,sys,runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
from studio import media,music,verify
score_overview=runpy.run_path(str(HERE/'score-overview.py'))['score']
from fontTools.ttLib import TTFont
RUN=Path('C:/video-studio-work/runs/portfolio-landscape/overview');SITE=Path('C:/Dev/VyasSathya.github.io')
PLAN=[('Talkover','talkover.mp4',2,6),('Kpop Sing','kpop-sing.mp4',.8,6),('Punchpad','punchpad.mp4',3,6),('Front of Line','front-of-line.mp4',2,6),('crewboard','crewboard.mp4',4,6),('agent-brain','agent-brain.mp4',14,6),('Mad Balls','mad-balls.mp4',0,9.4),('3D asset pipeline','asset-pipeline.mp4',2,6),('Whiteboard films','range-whiteboard.mp4',15,6)]
def run(a):subprocess.run([str(x) for x in a],cwd=RUN,check=True)
def main():
    RUN.mkdir(parents=True,exist_ok=True);font=TTFont(SITE/'fonts/geist-latin-500-normal.woff2');font.flavor=None;font.save(RUN/'geist.ttf');receipts=[];t=0;holds=[]
    for i,(name,file,start,duration) in enumerate(PLAN):
        source=SITE/'media'/file;target=RUN/f'clip-{i:02d}.mp4'
        y=984 if file=='agent-brain.mp4' else 28
        label='Kpop Sing / Marketing' if file=='kpop-sing.mp4' else name
        vf=f"scale=1920:1080:flags=lanczos,setsar=1,drawbox=x=1430:y={y}:w=460:h=66:color=black@0.85:t=fill,drawtext=fontfile=geist.ttf:text='{label}':fontcolor=white:fontsize=38:x=1450:y={y+10}"
        run([media.ffmpeg_bin(),'-y','-v','error','-ss',start,'-t',duration,'-i',source,'-an','-vf',vf,'-r',30,'-c:v','libx264','-crf',19,'-preset','fast','-pix_fmt','yuv420p',target])
        receipts.append(dict(project=name,source_file=file,source_start=start,duration=duration,timeline_start=t,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        # The only reading hold included from an accepted source is the final material comparison.
        if file=='asset-pipeline.mp4':holds.append([t,t+2])
        if file=='range-whiteboard.mp4':holds.append([t+4,t+duration])
        t+=duration
    end=RUN/'end.mp4';vf="drawtext=fontfile=geist.ttf:text='Vyas Sathya':fontcolor=white:fontsize=104:x=(w-tw)/2:y=430,drawtext=fontfile=geist.ttf:text='From idea to working product.':fontcolor=0xaaaaaa:fontsize=36:x=(w-tw)/2:y=570"
    run([media.ffmpeg_bin(),'-y','-v','error','-f','lavfi','-i','color=c=0x111214:s=1920x1080:r=30:d=3.5','-vf',vf,'-an','-c:v','libx264','-crf',19,'-preset','fast','-pix_fmt','yuv420p',end])
    (RUN/'concat.txt').write_text(''.join(f"file 'clip-{i:02d}.mp4'\n" for i in range(len(PLAN)))+"file 'end.mp4'\n",encoding='utf-8')
    run([media.ffmpeg_bin(),'-y','-v','error','-f','concat','-safe','0','-i',RUN/'concat.txt','-c','copy',RUN/'silent.mp4'])
    score_overview(t+3.5,RUN/'score.wav')
    final=RUN/'portfolio-overview-16x9.mp4';media.mux_loud(RUN/'silent.mp4',RUN/'score.wav',final,target=-14,peak=-3,crf=20)
    m=dict(width=1920,height=1080,duration=t+3.5,shots=receipts,holds=holds+[[t,t+3.5]],audio='Original locally synthesized electric-piano score, projects/portfolio-landscape/score-overview.py. Source films picture only; no source performance speech included.',tool='Existing video-studio ffmpeg, music and verify modules.',coverage='Nine selected case entries. No claim of films for all sixteen projects. Kpop performance is existing generated promotional footage; game is existing bot development capture.')
    (RUN/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');tech=verify.technical(final,m);(RUN/'technical.json').write_text(json.dumps(tech,indent=2));verify.log(RUN,1,'technical',tech)
    times=[s['timeline_start']+x for s in receipts for x in [.6,min(4.8,s['duration']-.5)]]+[t+2]
    frames=media.frames(final,RUN/'frames',times);verify.tile(frames,RUN/'strip.png',cols=3,width=640,labels=[str(round(x,1))+'s' for x in times]);print(json.dumps(tech))
if __name__=='__main__':main()
