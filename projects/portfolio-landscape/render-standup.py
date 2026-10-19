"""Source-preserving landscape excerpts from Vyas's own public performance.

No interior edits, narration, captions, replacement music or audience audio.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from fontTools.ttLib import TTFont
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]))
from studio import media,verify
BASE=Path('C:/video-studio-work/runs/portfolio-landscape');RUN=BASE/'standup-after-zipper';SOURCE=BASE/'standup/original-studio-download.mp4'
CUTS=[dict(start=16.,end=81.2,reason='Owner-requested start after the zipper joke, before the next complete setup at about16.32s. Through the arranged-marriage response; next topic begins at81.48s.'),dict(start=408.,end=469.,reason='Complete club-seating sequence, from its setup through the audience response. The next setup begins at469.36s.')]
CROP=[0,535,720,405]
FOLLOW=json.loads((BASE/'standup/camera-follow.json').read_text())

def crop_y(source_t):
    if source_t<408:return 535
    t=source_t-408;anchors=FOLLOW['anchors']
    for (a,y0),(b,y1) in zip(anchors,anchors[1:]):
        if t<=b:return round(y0+(y1-y0)*(t-a)/(b-a))
    return anchors[-1][1]

def run(args):return subprocess.run([str(a) for a in args],cwd=RUN,check=True)
def main():
    a=argparse.ArgumentParser();a.add_argument('--stills',action='store_true');args=a.parse_args();RUN.mkdir(exist_ok=True)
    rawframes=RUN/'crop-check';rawframes.mkdir(exist_ok=True)
    times=[17,28,54,63,78,410,429,435,440,450,458,462,463,464,465,466,467,468];frames=[]
    for i,t in enumerate(times):
        target=rawframes/f'frame-{i:02d}.png';run([media.ffmpeg_bin(),'-y','-v','error','-ss',t,'-i',SOURCE,'-frames:v','1','-vf',f'crop=720:405:0:{crop_y(t)},scale=1920:1080:flags=lanczos',target]);frames.append(target)
    verify.tile(frames,RUN/'crop-sheet.png',cols=3,labels=[str(t)+'s source' for t in times])
    if args.stills:return
    font=TTFont('C:/Dev/VyasSathya.github.io/fonts/geist-latin-500-normal.woff2');font.flavor=None;font.save(RUN/'geist.ttf')
    total=sum(c['end']-c['start'] for c in CUTS)
    filt=[];inputs=[]
    for i,c in enumerate(CUTS):
        inputs+=['-ss',str(c['start']),'-t',str(c['end']-c['start']),'-i',str(SOURCE)]
        y='535' if i==0 else FOLLOW['expression']
        filt.append(f"[{i}:v]setpts=PTS-STARTPTS,crop=720:405:0:'{y}',scale=1920:1080:flags=lanczos,setsar=1[v{i}]")
        filt.append(f'[{i}:a]aresample=48000,asetpts=PTS-STARTPTS[a{i}]')
    concat=''.join(f'[v{i}][a{i}]' for i in range(len(CUTS)))+f'concat=n={len(CUTS)}:v=1:a=1[v][a]'
    title="drawbox=x=45:y=920:w=335:h=90:color=black@0.6:t=fill:enable='lt(t,4)',drawtext=fontfile=geist.ttf:text='Vyas Sathya':fontcolor=white:fontsize=42:x=70:y=940:enable='lt(t,4)'"
    end=f"drawbox=x=0:y=0:w=iw:h=ih:color=0x111214:t=fill:enable='gte(t,{total-2.5})',drawtext=fontfile=geist.ttf:text='Vyas Sathya':fontcolor=white:fontsize=104:x=(w-tw)/2:y=430:enable='gte(t,{total-2.5})',drawtext=fontfile=geist.ttf:text='Stand-up':fontcolor=0xaaaaaa:fontsize=36:x=(w-tw)/2:y=570:enable='gte(t,{total-2.5})'"
    filters=';'.join(filt+[concat,f'[v]{title},{end}[outv]',f'[a]afade=t=in:d=0.03,afade=t=out:st={total-.10}:d=0.10[outa]'])
    run([media.ffmpeg_bin(),'-y','-v','error',*inputs,'-filter_complex',filters,'-map','[outv]','-map','[outa]','-r','30','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','pcm_s16le',RUN/'performance-edit.mkv'])
    run([media.ffmpeg_bin(),'-y','-v','error','-i',RUN/'performance-edit.mkv','-map','0:a','-c:a','pcm_s16le',RUN/'original-room.wav'])
    final=RUN/'standup-highlights-16x9.mp4';media.mux_loud(RUN/'performance-edit.mkv',RUN/'original-room.wav',final,target=-14,peak=-3,crf=20)
    m=dict(source=SOURCE.name,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_url='https://www.youtube.com/watch?v=o2yYGrDhbDE',retrieval='YouTube Studio owner Download control. Studio explicitly displayed Your video, comedy set.',duration=total,cuts=CUTS,crop=CROP,output_size=[1920,1080],holds=[],audio='The original performance and room audio, in the same source spans. Only global loudness normalization and 30/100ms edge fades. No music, synthetic speech, substituted response or internal time edits.',endcard=dict(start=total-2.5,reason='Shown during the retained source audience response, after the final punchline.'),transcript_status='Local machine transcript and YouTube auto captions are navigation aids, not corrected or published as Vyas wording. No subtitles generated.',selection_status='Editorial selection for review, not a claim that these are the best bits or verified laugh counts.')
    m['holds']=[[total-2.5,total]]
    m['audio']='Original performance and room audio in the same uninterrupted source spans. Two-pass loudness normalization includes dynamic range and true peak control, with 30/100ms edge fades. No music, synthetic speech, substituted response or internal time edits.'
    m['camera_follow']=dict(anchors=FOLLOW['anchors'],method='Source camera-follow reframing. Detector suggestions were reviewed as composition aids; false-positive body detections are not accepted as a framing test. Dense source frames around the late camera movement were visually inspected.')
    (RUN/'edit-manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
    tech=verify.technical(final,m);(RUN/'technical.json').write_text(json.dumps(tech,indent=2));verify.log(RUN,1,'render',tech)
    ts=[.5,10,20,35,45,63,66,85,105,total-3,total-1];frames=media.frames(final,RUN/'frames',ts);verify.tile(frames,RUN/'strip.png',cols=3,labels=[str(round(t,2))+'s edit' for t in ts]);print(json.dumps(tech))
if __name__=='__main__':main()
