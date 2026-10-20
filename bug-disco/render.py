"""The Six-Shoe Shuffle. Original vector animation + local Flite speech.
Run: python render.py (Pillow, NumPy, FFmpeg with libflite required).
Vocabulary source: apestogetherstronger/emmaenglish2/dist/data/dictionary.json.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np, subprocess, math, json, wave
P=Path(__file__).resolve().parent
W,H,FPS,SR=960,540,24,44100
TAU=math.tau
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fonts={}
def font(n,bold=False):
 k=(n,bold)
 if k not in fonts:fonts[k]=ImageFont.truetype(BOLD if bold else FONT,n)
 return fonts[k]
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
scenes=[
 ('SHOES REQUIRED', [('bee','Welcome to the bug disco! Shoes required.')], 'bee',5),
 ('A SMALL PROBLEM', [('spider','Eight shoes, please.'),('bee','Six. Best I can do.')], 'shoes',6),
 ('LET US COUNT', [('bee','One. Two. Three. Four. Five. Six.')], 'count',6),
 ('TWO FEET LEFT OVER', [('spider','Great! Now, what about these two?')], 'legs',5),
 ('BEE.EXE HAS STOPPED', [('robot','Error! Too many feet!')], 'six',4),
 ('TINY SCIENCE BREAK', [('narrator','Insects, like bees, have six legs.')], 'six',5),
 ('SAME PARTY. DIFFERENT BODY.', [('narrator','Spiders have eight legs. They are arachnids, not insects.')], 'spider',7),
 ('A BRILLIANT IDEA', [('bee','I can fly! I do not need shoes!')], 'fly',5),
 ('FREE DELIVERY', [('spider','Then I can have yours!')], 'shoes',4.5),
 ('THE CAKE INCIDENT', [('bee','You took my cake!'),('spider','No. I am sharing!')], 'sharing',6),
 ('THE SIX-SHOE SHUFFLE', [('narrator','Six legs. Eight legs. Everyone can dance!')], 'dance',5.5),
 ('YOUR TURN', [('narrator','How many legs does a spider have?')], 'count',6),
 ('EIGHT! YOU GOT IT.', [('spider','Eight legs. And one very happy spider!')], 'spider',5)
]
# Make voice clips first, then fit each scene to its spoken lines.
clips=[]; timeline=[]; cursor=0
for si,(title,lines,word,minimum) in enumerate(scenes):
 local=.65; events=[]
 for li,(speaker,text) in enumerate(lines):
  (P/'line.txt').write_text(text)
  voice={'bee':'slt','spider':'awb','narrator':'slt','robot':'kal'}[speaker]
  out=P/f'voice-{si}-{li}.wav'
  pitch={'bee':1.1,'spider':1.0,'narrator':1.0,'robot':.93}[speaker]
  subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i',f'flite=textfile={P / "line.txt"}:voice={voice}', '-af',f'asetrate=16000*{pitch},aresample={SR},atempo=0.94','-ac','1',str(out)],check=True)
  with wave.open(str(out),'rb') as f: a=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float)/32768
  dur=len(a)/SR;events.append({'speaker':speaker,'text':text,'start':local,'end':local+dur});clips.append((cursor+local,a));local+=dur+.42
 length=max(minimum,local+.65);timeline.append({'start':cursor,'end':cursor+length,'title':title,'word':word,'events':events});cursor+=length
DURATION=math.ceil(cursor*FPS)/FPS
(P/'timeline.json').write_text(json.dumps(timeline,indent=2))
# Original bouncy marimba-like backing and comic sound effects.
ts=np.arange(int(DURATION*SR))/SR; audio=np.zeros(len(ts))
for start,a in clips:
 i=int(start*SR); audio[i:i+len(a)]+=a*.83
notes=[261.63,329.63,392,329.63,293.66,349.23,440,392]
for j,st in enumerate(np.arange(0,DURATION,.32)):
 i=int(st*SR);u=np.arange(int(.27*SR))/SR;f=notes[j%8]/(2 if j%4==0 else 1)
 a=.035*np.sin(TAU*f*u)*np.exp(-u*18)+.012*np.sin(TAU*f*3*u)*np.exp(-u*30)
 n=min(len(a),len(audio)-i); audio[i:i+n]+=a[:n]
def effect(st,kind):
 i=int(st*SR);u=np.arange(int(.35*SR))/SR
 if kind=='boing':a=.11*np.sin(TAU*(220*u+110*u*u))*np.exp(-u*8)
 elif kind=='buzz':a=.07*np.sin(TAU*120*u)*(np.sin(TAU*25*u)>0)*np.exp(-u*7)
 else:a=.1*np.sin(TAU*(900*u-800*u*u))*np.exp(-u*12)
 n=min(len(a),len(audio)-i);audio[i:i+n]+=a[:n]
for si in [1,3,4,7,8,9]:effect(timeline[si]['start']+.12,'buzz' if si==4 else 'boing')
for j in range(8):effect(timeline[10]['start']+j*.55,'ping')
audio=np.tanh(audio)*.87; stereo=np.stack([audio,audio],axis=1)
with wave.open(str(P/'mix.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((stereo*32767).astype('<i2').tobytes())
# Drawing helpers: expressive, original code-native cartoon characters.
INK='#24223b';YELLOW='#ffcb45';PURPLE='#8e64d8';PINK='#ff6e9e'
def txt(d,xy,s,size=22,fill=INK,bold=False,anchor='mm'):
 d.text(xy,s,font=font(size,bold),fill=fill,anchor=anchor)
def rr(d,box,fill,r=18,outline=None,width=2):d.rounded_rectangle(tuple(map(int,box)),r,fill=fill,outline=outline,width=width)
def ell(d,box,fill,outline=None,width=2):d.ellipse(tuple(map(int,box)),fill=fill,outline=outline,width=width)
def shoe(d,x,y,color='#fc725f',scale=1,angle=0):
 # Oversized rounded dancing shoe with a cream sole.
 sw,sh=34*scale,19*scale
 rr(d,(x-sw/2,y-sh/2,x+sw/2+8*scale,y+sh/2),color,7,INK,2)
 d.line((x-sw/2+2,y+sh/2-3,x+sw/2+5*scale,y+sh/2-3),fill='#fff3d7',width=max(2,int(4*scale)))
 d.line((x-2,y-sh/2+3,x+7,y-sh/2+3),fill=INK,width=2)
def face(d,cx,cy,scale,t,speaking=False,mood='happy',look=0):
 blink=(t%4.3)<.13
 for s in [-1,1]:
  xx=cx+s*22*scale; yy=cy-5*scale
  if blink:d.line((xx-10*scale,yy,xx+10*scale,yy),fill=INK,width=max(2,int(4*scale)))
  else:
   ell(d,(xx-13*scale,yy-18*scale,xx+13*scale,yy+14*scale),'white',INK)
   ell(d,(xx-5*scale+look,yy-6*scale,xx+6*scale+look,yy+9*scale),INK)
   ell(d,(xx+look,yy-5*scale,xx+4*scale+look,yy-1*scale),'white')
 if speaking and math.sin(t*23)>.0:
  ell(d,(cx-11*scale,cy+23*scale,cx+11*scale,cy+45*scale),INK)
  ell(d,(cx-6*scale,cy+36*scale,cx+6*scale,cy+43*scale),PINK)
 elif mood=='shock':ell(d,(cx-9*scale,cy+24*scale,cx+9*scale,cy+43*scale),INK)
 else:d.arc((cx-17*scale,cy+10*scale,cx+17*scale,cy+40*scale),0,180,fill=INK,width=max(2,int(3*scale)))
 for s in [-1,1]:ell(d,(cx+s*43*scale-9*scale,cy+18*scale,cx+s*43*scale+9*scale,cy+27*scale),'#f49d93')
def bee(d,cx,cy,t,scale=1,speaking=False,mood='happy',dance=False,fly=False,shoes=False,numbers=False):
 def p(x,y):return (cx+x*scale,cy+y*scale)
 # Six legs, three on each side, all visibly attached to the thorax.
 for side in [-1,1]:
  for j in range(3):
   swing=math.sin(t*8+j)*10 if dance or fly else math.sin(t*2+j)*3
   a=p(side*37,-8+j*20);b=p(side*(70+j*8),15+j*20+swing);c=p(side*(94+j*7),40+j*24+swing)
   d.line([a,b,c],fill=INK,width=max(2,int(5*scale)))
   if shoes:shoe(d,*c,scale=scale*.7)
   else:ell(d,(c[0]-5*scale,c[1]-3*scale,c[0]+5*scale,c[1]+3*scale),INK)
   if numbers:
    n=j+1 if side==-1 else j+4
    ell(d,(c[0]-14,c[1]+9,c[0]+14,c[1]+37),'white',INK);txt(d,(c[0],c[1]+23),str(n),18,bold=True)
 # Wings behind body.
 wing=math.sin(t*(35 if fly else 5))*8
 for side in [-1,1]:
  a=p(side*65-30,-60-wing);b=p(side*65+30,8)
  ell(d,(*a,*b),'#e1faff','#76bcc7',3)
 ell(d,(*p(-54,-10),*p(54,96)),YELLOW,INK,3)
 for yy in [16,42,68]:d.line((*p(-44,yy),*p(44,yy)),fill=INK,width=max(2,int(12*scale)))
 ell(d,(*p(-60,-92),*p(60,15)),YELLOW,INK,3)
 for side in [-1,1]:
  d.line([p(side*24,-85),p(side*35,-113),p(side*49,-115)],fill=INK,width=max(2,int(4*scale)));ell(d,(*p(side*49-5,-120),*p(side*49+5,-110)),INK)
 face(d,cx,cy-50*scale,scale,t,speaking,mood,3)
def spider(d,cx,cy,t,scale=1,speaking=False,dance=False,shoes=0,numbers=False,extra=False):
 def p(x,y):return (cx+x*scale,cy+y*scale)
 for side in [-1,1]:
  for j in range(4):
   swing=math.sin(t*8+j*1.8)*17 if dance else math.sin(t*2+j)*3
   if extra and j==3:swing=-55+math.sin(t*7)*8
   a=p(side*40,-15+j*16);b=p(side*(89+j*12),-38+j*20+swing);c=p(side*(123+j*11),45+j*15+swing)
   d.line([a,b,c],fill=INK,width=max(2,int(6*scale)))
   # The first three on each side wear the original six shoes.
   if j<3 and shoes>=6 or j==3 and shoes>=8:shoe(d,*c,scale=scale*.8,color='#62cbaf' if j==3 else '#fc725f')
   else:ell(d,(c[0]-6*scale,c[1]-3*scale,c[0]+6*scale,c[1]+4*scale),INK)
   if numbers:
    n=j+1 if side==-1 else j+5
    ell(d,(c[0]-9,c[1]+10,c[0]+9,c[1]+28),'white',INK);txt(d,(c[0],c[1]+19),str(n),13,bold=True)
 ell(d,(*p(-74,-34),*p(74,90)),PURPLE,INK,3)
 ell(d,(*p(-64,-85),*p(64,24)),'#ad87e9',INK,3)
 face(d,cx,cy-44*scale,scale,t,speaking,'happy',-3)
 # A jaunty party hat is clearly not an extra limb.
 d.polygon([p(-18,-78),p(3,-135),p(26,-78)],fill=PINK,outline=INK)
 ell(d,(*p(-3,-142),*p(9,-130)),YELLOW)
def cake(d,cx,cy,t,bite=False):
 ell(d,(cx-75,cy+32,cx+75,cy+49),'#c4c7d4')
 rr(d,(cx-59,cy-20,cx+59,cy+35),'#f5ae81',8,INK,3)
 d.line((cx-58,cy+9,cx+58,cy+9),fill='#bc5e52',width=9)
 rr(d,(cx-61,cy-31,cx+61,cy-8),'#fff2cf',10,INK,3)
 for i in range(7):ell(d,(cx-55+i*17,cy-19,cx-43+i*17,cy),'#fff2cf')
 for i in [-30,0,30]:ell(d,(cx+i-7,cy-40,cx+i+7,cy-27),'#e95862')
 if bite:ell(d,(cx+25,cy-36,cx+77,cy+25),'#faf3de')
def bubble(d,text,cx,cy,color='white',width=390):
 # Word-wrap speech bubbles; occupy separate rows from vocabulary/subtitles.
 words=text.split();lines=[];line=''
 for word in words:
  trial=(line+' '+word).strip()
  if d.textlength(trial,font=font(23,True))>width-38:lines.append(line);line=word
  else:line=trial
 if line:lines.append(line)
 hh=28*len(lines)+25
 rr(d,(cx-width/2,cy-hh/2,cx+width/2,cy+hh/2),color,17,INK,3)
 d.polygon([(cx-15,cy+hh/2-2),(cx+9,cy+hh/2-2),(cx-8,cy+hh/2+15)],fill=color)
 for i,l in enumerate(lines):txt(d,(cx,cy-hh/2+25+i*28),l,23,bold=True)
def draw(t):
 si=next((i for i,s in enumerate(timeline) if s['start']<=t<s['end']),len(timeline)-1)
 s=timeline[si];u=t-s['start'];q=u/(s['end']-s['start'])
 im=Image.new('RGB',(W,H),'#faf3de');d=ImageDraw.Draw(im)
 # Warm paper stage, bold corner labels, moving disco lights later.
 d.rectangle((0,0,W,67),fill=INK)
 txt(d,(30,33),'EMMA ENGLISH  /  BUG DISCO',16,'#fff3d7',True,'lm')
 txt(d,(929,33),f'{si+1:02d} / {len(timeline):02d}',14,'#bcb4d7',False,'rm')
 txt(d,(480,95),s['title'],27,INK,True)
 d.ellipse((-100,315,500,580),fill='#eedfb9');d.ellipse((430,335,1100,610),fill='#e9ddbd')
 d.line((0,419,W,419),fill='#d2c5a5',width=2)
 # Flower-like wall decorations and hanging disco ball.
 if si in [0,10,11,12]:
  for k in range(8):
   xx=70+k*120; col=['#ffd565','#bfa6ec','#b9e8d6'][k%3]; ell(d,(xx-19,155,xx+19,193),col)
  d.line((480,120,480,145),fill=INK,width=2);ell(d,(449,145,511,207),'#c6dfe9',INK,2)
  for n in [-15,0,15]:d.line((480+n,150,480+n,202),fill='#88adbe',width=1)
  for n in [163,176,189]:d.line((452,n,508,n),fill='#88adbe',width=1)
 ev=next((e for e in s['events'] if e['start']<=u<e['end']),None)
 speaker=ev['speaker'] if ev else ''
 bx,by,sx,sy=265,309,695,312
 if si==5:
  bee(d,360,290,t,1.16,speaking=False,numbers=True)
  txt(d,(765,265),'6',110,'#bd8200',True);txt(d,(765,350),'LEGS',25,bold=True)
  rr(d,(640,380,885,415),'#ffdc75',10);txt(d,(762,398),'BEE = INSECT',18,bold=True)
 elif si==6:
  spider(d,350,292,t,1.0,numbers=True)
  txt(d,(770,245),'8',110,'#7b4cbe',True);txt(d,(770,328),'LEGS',25,bold=True)
  rr(d,(615,358,925,403),'#dcc9f8',10);txt(d,(770,380),'SPIDER = ARACHNID',18,bold=True)
 else:
  flying=si in [7,8]
  if si==7:by-=smooth((u-.9)/2.2)*110;bx+=math.sin(u*3)*13
  if si==8:by=190+math.sin(u*6)*10;bx=240+math.sin(u*2)*40
  dancing=si in [10,12]
  if dancing:bx+=math.sin(t*8)*15;sx+=math.sin(t*8+2)*18;by+=abs(math.sin(t*8))*12;sy+=abs(math.sin(t*8+2))*12
  bee(d,bx,by,t,.86,speaker in ['bee','robot'],'shock' if si in [3,4,9] else 'happy',dancing,flying,si in [0,1,2,3,4,7])
  spider(d,sx,sy,t,.86,speaker=='spider',dancing,0 if si==0 else 6 if si<8 else 8,extra=si in [3,4])
  if si==0:
   rr(d,(390,275,560,394),'#78cfb4',12,INK,3);txt(d,(475,300),'BUG',26,bold=True);txt(d,(475,335),'DISCO',26,bold=True);txt(d,(475,374),'TONIGHT!',14,bold=True)
  if si==1:
   for j in range(3):shoe(d,430+j*43,365,scale=.9)
  if si==2:
   count=min(6,int(u/.72)+1)
   for j in range(count):
    shoe(d,374+(j%3)*50,280+(j//3)*65,scale=.8)
    txt(d,(380+(j%3)*50,309+(j//3)*65),str(j+1),20,bold=True)
  if si==3:
   txt(d,(480,318),'... + 2?',38,'#c95454',True)
   for x in [550,840]:txt(d,(x,360),'?',35,'#c95454',True)
  if si==4:
   rr(d,(355,275,584,385),'#ffccc3',14,INK,3);txt(d,(470,306),'404',39,'#b33c43',True);txt(d,(470,352),'SHOES NOT FOUND',14,bold=True)
   for k in range(4):d.line((bx-60+k*30,by-135,bx-65+k*30,by-158),fill='#e25f5f',width=4)
  if si==7:
   for j in range(6):
    v=np.clip((u-1-j*.1)/1.4,0,1)
    if v<1:shoe(d,bx+(j-2.5)*25,by+70+float(v)*170,scale=.7)
  if si==8:
   txt(d,(470,307),'SPECIAL DELIVERY!',20,'#8751be',True)
   if q<.55:
    for j in range(2):shoe(d,340+q*500+j*45,250-100*math.sin(q*math.pi*2)+j*30,scale=.9,color='#62cbaf')
  if si==9:
   cake(d,490,350,t,bite=u>2.5)
   if u>3.7:txt(d,(480,264),'"SHARING"',24,'#a94567',True)
  if dancing:
   for j in range(28):
    xx=(j*137+int(t*45))%960;yy=140+(j*53+int(t*80))%260
    d.rectangle((xx,yy,xx+5,yy+9),fill=['#f783a0','#9976d1','#edb72b','#56b998'][j%4])
  if si==11:
   rr(d,(380,255,580,380),INK,18);txt(d,(480,290),'6  or  8?',31,'#fff4d4',True)
   txt(d,(480,343),'YOUR GUESS!',17,'#b7e9db',True)
  if si==12:txt(d,(480,306),'8!',80,'#7c4bc0',True)
 # Dialogue at top of stage, always away from character faces.
 if ev and speaker not in ['narrator']:
  bubble(d,ev['text'],620 if si==7 else 285 if speaker in ['bee','robot'] else 680,176,'#fff0b8' if speaker in ['bee','robot'] else '#eadbff',420)
 # Permanently readable subtitles (also provided as a VTT track).
 d.rectangle((0,432,W,540),fill=INK)
 word=s['word'];rr(d,(23,447,180,485),'#ffda69',12);txt(d,(101,467),word.upper(),21,INK,True)
 subtitle=ev['text'] if ev else ('Say it: '+word+'!' if si not in [11,12] else 'How many legs does a spider have?' if si==11 else 'Eight legs. A spider is an arachnid.')
 words=subtitle.split();lines=[];line=''
 for w in words:
  trial=(line+' '+w).strip()
  if d.textlength(trial,font=font(21))>710:lines.append(line);line=w
  else:line=trial
 lines.append(line)
 for j,line in enumerate(lines):txt(d,(202,456+j*27),line,21,'#fff8e5',False,'lm')
 txt(d,(25,516),'THE SIX-SHOE SHUFFLE',11,'#aba6bf',False,'lm')
 d.rectangle((200,513,934,517),fill='#49445d');d.rectangle((200,513,200+734*t/DURATION,517),fill='#a8decf')
 return im
# Encode actual video; no browser dependencies or runtime generation needed.
proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(P/'mix.wav'),'-c:v','libx264','-preset','fast','-crf','26','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-shortest','-movflags','+faststart',str(P/'bug-disco.mp4')],stdin=subprocess.PIPE)
for i in range(int(DURATION*FPS)):
 proc.stdin.write(draw(i/FPS).tobytes())
 if i%240==0:print(f'Rendering {i/FPS:.0f}/{DURATION:.0f}s',flush=True)
proc.stdin.close();assert proc.wait()==0
draw(timeline[3]['start']+1.2).save(P/'poster.jpg',quality=90)
# Contact sheet of real frames for visual verification.
contact=Image.new('RGB',(960,270*7),'white')
for i,s in enumerate(timeline):
 thumb=draw(s['start']+min(1.8,(s['end']-s['start'])/2)).resize((480,270));contact.paste(thumb,((i%2)*480,(i//2)*270))
contact.save(P/'contact.jpg')
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
vtt=['WEBVTT','']
for s in timeline:
 for e in s['events']:vtt.extend([f'{stamp(s["start"]+e["start"])} --> {stamp(s["start"]+e["end"])}',e['speaker'].upper()+': '+e['text'],''])
(P/'captions.vtt').write_text('\n'.join(vtt))
print('DONE',DURATION,(P/'bug-disco.mp4').stat().st_size,flush=True)
