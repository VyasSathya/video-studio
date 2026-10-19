"""Replace only the overview soundtrack, preserving every encoded picture packet."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from studio import media

def call(args):
    return subprocess.run([media.ffmpeg_bin(),'-hide_banner',*map(str,args)],capture_output=True,text=True,check=True)

def picture_hash(path):
    return call(['-v','error','-i',path,'-map','0:v:0','-c','copy','-bsf:v','h264_mp4toannexb','-f','hash','-hash','sha256','-']).stdout.strip()

def replace(video,audio,output):
    first=call(['-i',audio,'-af','loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json','-f','null','-']).stderr
    measured=json.JSONDecoder().raw_decode(first[first.rfind('{'):])[0]
    filt='loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}'.format(**measured)
    call(['-y','-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',filt,'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart','-shortest',output])
    before,after=picture_hash(video),picture_hash(output)
    assert before==after,'Picture stream changed'
    dur_before,dur_after=media.duration(video),media.duration(output)
    assert abs(dur_before-dur_after)<.05,(dur_before,dur_after)
    check=call(['-i',output,'-af','loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json','-f','null','-']).stderr
    loudness=json.JSONDecoder().raw_decode(check[check.rfind('{'):])[0]
    assert abs(float(loudness['input_i'])+14)<1,loudness
    assert float(loudness['input_tp'])<=-1,loudness
    result={'video_file':video.name,'audio_file':audio.name,'output_file':output.name,'picture_sha256_before':before,'picture_sha256_after':after,'picture_unchanged':True,'duration_before':dur_before,'duration_after':dur_after,'loudness':loudness,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.audio-review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',type=Path,required=True);p.add_argument('--audio',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(replace(a.video,a.audio,a.out),indent=2))
