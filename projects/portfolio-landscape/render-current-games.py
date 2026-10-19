"""Real current-source bot captures, with source hashes and no gameplay alterations."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from fontTools.ttLib import TTFont
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
from studio import media,music,verify
BASE=Path('C:/video-studio-work/runs/portfolio-landscape')
SITE=Path(os.environ.get('PORTFOLIO_SITE_ROOT','C:/Dev/VyasSathya.github.io'))
def main():
    for key,name,start,duration in [('brainrot','Brainrot Brawl',8,24),('hook-wars','Hook Wars',3,30)]:
        source=BASE/'current-games-capture'/key/(key+'-current.mp4');run=BASE/(key+'-current');run.mkdir(exist_ok=True)
        font=TTFont(SITE/'fonts/geist-latin-500-normal.woff2');font.flavor=None;font.save(run/'geist.ttf')
        total=duration+2.5
        title=f"drawbox=x=35:y=28:w=550:h=65:color=black@0.75:t=fill:enable='lt(t,4)',drawtext=fontfile=geist.ttf:text='{name}':fontsize=34:fontcolor=white:x=55:y=41:enable='lt(t,4)'"
        end=f"drawtext=fontfile=geist.ttf:text='{name}':fontsize=96:fontcolor=white:x=(w-tw)/2:y=470"
        cmd=[media.ffmpeg_bin(),'-y','-v','error','-ss',start,'-t',duration,'-i',source,'-f','lavfi','-i','color=c=0x111214:s=1920x1080:r=30:d=2.5','-filter_complex',f'[0:v]setpts=PTS-STARTPTS,{title}[a];[1:v]{end}[b];[a][b]concat=n=2:v=1:a=0[v]','-map','[v]','-an','-r','30','-c:v','libx264','-crf','19','-preset','fast','-pix_fmt','yuv420p',run/'silent.mp4']
        subprocess.run([str(x) for x in cmd],cwd=run,check=True)
        music.bed(total,run/'score.wav',mood='focus',seed=11 if key=='brainrot' else 23)
        final=run/(key+'-16x9.mp4');media.mux_loud(run/'silent.mp4',run/'score.wav',final,target=-14,peak=-3,crf=20)
        m={'name':name,'width':1920,'height':1080,'duration':total,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_range':[start,start+duration],'capture_receipt':str(BASE/'current-games-capture/source-receipt.json'),'holds':[[duration,total]],'audio':'Original local instrumental bed; capture has no game audio. No synthetic performance or fabricated gameplay.','scope':'Current local working tree, real six-bot development match. Camera presentation only; no game behavior or mechanics changes.'}
        (run/'manifest.json').write_text(json.dumps(m,indent=2));tech=verify.technical(final,m);(run/'technical.json').write_text(json.dumps(tech,indent=2));verify.log(run,1,'technical',tech)
        ts=[.7,5,10,15,20,duration-.5,total-1];frames=media.frames(final,run/'frames',ts);verify.tile(frames,run/'strip.png',cols=3,labels=[str(x)+'s' for x in ts]);print(json.dumps({'project':key,'technical':tech}),flush=True)
if __name__=='__main__':main()
