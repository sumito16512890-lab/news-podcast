# キャッシュ済みチャンクを、つなぎ目にフェードを入れて結合する
import os,sys,hashlib,wave,array
M,V,S=os.environ['MODEL'],os.environ['VOICE'],os.environ['STYLE']
src,n,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
paras=[p.strip() for p in open(src).read().split('\n') if p.strip()];ch=[];cur=''
for p in paras:
    if cur and len(cur)+len(p)>n: ch.append(cur);cur=''
    cur+=p+'\n'
ch.append(cur)
F=int(24000*0.03)  # 30ms フェード
allpcm=array.array('h')
for c in ch:
    a=array.array('h',open('cache/'+hashlib.md5((M+V+S+c).encode()).hexdigest()+'.pcm','rb').read())
    # Gemini が各チャンクの末尾に出す約0.1秒のフルスケール雑音を切り落とす
    for i in range(max(0,len(a)-int(24000*0.5)),len(a)):
        if abs(a[i])>31000:
            print('trimmed tail noise at',round(i/24000,2),'of',round(len(a)/24000,2)); del a[max(0,i-480):]; break
    for i in range(min(F,len(a))):
        g=i/F; a[i]=int(a[i]*g); a[-1-i]=int(a[-1-i]*g)
    allpcm.extend(a); allpcm.extend(array.array('h',[0]*int(24000*0.6)))
w=wave.open(out,'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(allpcm.tobytes());w.close()
print(len(ch),'chunks',len(allpcm)/24000,'s')
