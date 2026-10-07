import json,urllib.request,os,sys,base64,time,subprocess,wave
k=os.environ.get('GEMINI_API_KEY') or open(os.path.expanduser('~/.config/gemini/key')).read().strip()
MODEL=os.environ.get('MODEL','gemini-3.8-flash-tts'); VOICE=os.environ.get('VOICE','Kore')
src,out=sys.argv[1],sys.argv[2]; limit=int(os.environ.get('LIMIT','0'))
paras=[p.strip() for p in open(src).read().split('\n') if p.strip()]
chunks=[];cur=''
for p in paras:
    if cur and len(cur)+len(p)>int(os.environ.get('CHUNK','1200')): chunks.append(cur);cur=''
    cur+=p+'\n'
if cur: chunks.append(cur)
if limit: chunks=chunks[:limit]
pcm=b''
import hashlib
os.makedirs('cache',exist_ok=True)
for i,c in enumerate(chunks):
    cf='cache/'+hashlib.md5((MODEL+VOICE+os.environ.get('STYLE','')+c).encode()).hexdigest()+'.pcm'
    if os.path.exists(cf):
        pcm+=open(cf,'rb').read()+b'\0'*int(24000*2*0.6); print(f'chunk {i+1} cached',flush=True); continue
    body={"contents":[{"parts":[{"text":(os.environ.get("STYLE","").strip()+"\n\n"+c).strip()}]}],
          "generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":VOICE}}}}}
    for a in range(5):
        try:
            r=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",data=json.dumps(body).encode(),headers={'x-goog-api-key':k,'Content-Type':'application/json'})
            d=json.load(urllib.request.urlopen(r,timeout=300))
            a_=base64.b64decode(d['candidates'][0]['content']['parts'][0]['inlineData']['data']); open(cf,'wb').write(a_); pcm+=a_
            pcm+=b'\0'*int(24000*2*0.6)
            print(f'chunk {i+1}/{len(chunks)} ok',flush=True); break
        except urllib.error.HTTPError as e:
            msg=e.read().decode()[:300]; print('ERR',e.code,msg,flush=True)
            if e.code in (500,503): time.sleep(20*(a+1)); continue
            sys.exit(1)
        except Exception as e:
            print('ERR',e,flush=True); time.sleep(10)
    else: sys.exit(1)
w=wave.open(out+'.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm);w.close()
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',out+'.wav','-b:a','64k',out],check=True)
print('done',len(pcm)/48000,'sec')
