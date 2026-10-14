import json,urllib.request,os,sys,base64,time,subprocess,wave,hashlib
import voicecheck
k=os.environ.get('GEMINI_API_KEY') or open(os.path.expanduser('~/.config/gemini/key')).read().strip()
MODEL=os.environ.get('MODEL','gemini-3.8-flash-tts'); VOICE=os.environ.get('VOICE','Kore')
STYLE=os.environ.get('STYLE','')
src,out=sys.argv[1],sys.argv[2]; limit=int(os.environ.get('LIMIT','0'))
# 声の高さが全体から何割ずれたら作り直すか／作り直しの最大回数（無料枠を使い切らないよう少なめ）
TOL=float(os.environ.get('PITCH_TOL','0.06')); RETRY=int(os.environ.get('PITCH_RETRY','4'))
paras=[p.strip() for p in open(src).read().split('\n') if p.strip()]
chunks=[];cur=''
for p in paras:
    if cur and len(cur)+len(p)>int(os.environ.get('CHUNK','1200')): chunks.append(cur);cur=''
    cur+=p+'\n'
if cur: chunks.append(cur)
if limit: chunks=chunks[:limit]
os.makedirs('cache',exist_ok=True)
def cachefile(c): return 'cache/'+hashlib.md5((MODEL+VOICE+STYLE+c).encode()).hexdigest()+'.pcm'

def speak(c, tries=5):
    """1区切りを読み上げて PCM を返す。無料枠切れなどで続けられないときは None。"""
    body={"contents":[{"parts":[{"text":(STYLE.strip()+"\n\n"+c).strip()}]}],
          "generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":VOICE}}}}}
    for a in range(tries):
        try:
            r=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",data=json.dumps(body).encode(),headers={'x-goog-api-key':k,'Content-Type':'application/json'})
            d=json.load(urllib.request.urlopen(r,timeout=300))
            return base64.b64decode(d['candidates'][0]['content']['parts'][0]['inlineData']['data'])
        except urllib.error.HTTPError as e:
            msg=e.read().decode()[:300]; print('ERR',e.code,msg,flush=True)
            if e.code in (500,503): time.sleep(20*(a+1)); continue
            return None
        except Exception as e:
            print('ERR',e,flush=True); time.sleep(10)
    return None

# 1. 全区切りを読み上げる（作り済みの区切りはキャッシュを使う）
audio=[]
for i,c in enumerate(chunks):
    cf=cachefile(c)
    if os.path.exists(cf):
        audio.append(open(cf,'rb').read()); print(f'chunk {i+1} cached',flush=True); continue
    a_=speak(c)
    if a_ is None: sys.exit(1)
    open(cf,'wb').write(a_); audio.append(a_)
    print(f'chunk {i+1}/{len(chunks)} ok',flush=True)

# 2. 声の高さをそろえる：全体の中央値から大きくずれた区切りだけ作り直し、いちばん近いものを残す
p=[voicecheck.pitch(a) for a in audio]
ok=[x for x in p if x]
if len(ok)>=2:
    ref=sorted(ok)[len(ok)//2]
    print('pitch per chunk:',[round(x) if x else None for x in p],'reference',round(ref),flush=True)
    order=sorted([i for i in range(len(audio)) if p[i] and abs(p[i]/ref-1)>TOL],key=lambda i:-abs(p[i]/ref-1))
    left=RETRY
    for i in order:
        while left>0 and abs(p[i]/ref-1)>TOL:
            left-=1
            a_=speak(chunks[i],tries=2)
            if a_ is None: left=0; break
            q=voicecheck.pitch(a_)
            print(f'chunk {i+1} remade: {round(p[i])}Hz -> {round(q) if q else None}Hz',flush=True)
            if q and abs(q/ref-1)<abs(p[i]/ref-1):
                audio[i],p[i]=a_,q; open(cachefile(chunks[i]),'wb').write(a_)

pcm=b''.join(a+b'\0'*int(24000*2*0.6) for a in audio)
w=wave.open(out+'.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm);w.close()
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',out+'.wav','-b:a','64k',out],check=True)
print('done',len(pcm)/48000,'sec')
