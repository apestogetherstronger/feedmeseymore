"""Deterministic procedural short. Requires Python, numpy, Pillow, ffmpeg."""
import numpy as np, math, subprocess, wave
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
P=Path(__file__).resolve().parent
W,H,FPS,SECONDS=768,432,24,24
rng=np.random.default_rng(42)
y,x=np.mgrid[0:H,0:W]; X=(x-W/2)/H;Y=(y-H/2)/H
R=np.sqrt(X*X+Y*Y); A=np.arctan2(Y,X)
stars=rng.random((260,4))
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def ease(a,b,t):
 z=np.clip((t-a)/(b-a),0,1);return z*z*(3-2*z)
def frame(t):
 birth=ease(5,11,t);burst=ease(12,14,t); home=ease(17,22,t)
 arr=np.zeros((H,W,3),dtype=float);arr[:]=[2,5,15]
 swirl=(np.sin(A*3+R*23-t*.28)+1)/2
 cloud=np.exp(-R*R*4)*(swirl**3)*(.6+.4*np.sin(R*30-t*.4)**2)
 arr+=cloud[:,:,None]*np.array([35,27,90])*(1-home)
 core=np.exp(-R*R/(.001+birth*.007))*(birth*(1-burst))
 halo=np.exp(-R*9)*birth*(1-burst)
 arr+=core[:,:,None]*np.array([255,225,165])+halo[:,:,None]*np.array([110,50,15])
 shell=np.exp(-((R-(t-13)*.11)/.035)**2)*ease(12.8,13.3,t)*(1-ease(16,20,t))
 arr+=shell[:,:,None]*np.array([100,140,200])
 # A fictional world emerging beneath a blue atmospheric arc.
 pr=np.sqrt(X*X+(Y-1.2)**2)
 atmo=np.exp(-((pr-1.1)/.017)**2)*home
 arr+=atmo[:,:,None]*np.array([40,140,220])
 planet=pr<1.09
 arr[planet]=arr[planet]*(1-home)+np.array([2,7,17])*home
 sun=np.exp(-((X-.24)**2+(Y-.126)**2)/.001)*home
 arr+=sun[:,:,None]*np.array([230,190,110])
 im=Image.fromarray(np.uint8(np.clip(arr,0,255))); d=ImageDraw.Draw(im)
 for sx,sy,sz,phase in stars:
  xx=(sx*W+(sx-.5)*t*1.5)%W; yy=(sy*H+(sy-.5)*t*.7)%H
  if home>.2 and ((xx-W/2)/H)**2+((yy-H/2)/H-1.2)**2<1.09**2: continue
  v=int((90+140*sz)*(.75+.25*math.sin(t*.8+phase*6)))
  d.ellipse((xx,yy,xx+1+sz,yy+1+sz),fill=(v,v,min(255,v+25)))
 def label(text,yy,size,alpha=1):
  f=ImageFont.truetype(font,size); box=d.textbbox((0,0),text,font=f); d.text(((W-(box[2]-box[0]))/2,yy),text,font=f,fill=tuple(int(c*alpha) for c in (229,234,246)))
 if t<6:
  a=ease(.5,2,t)*(1-ease(4.5,6,t));label('THE LAST LIGHT',H*.38,36,a);label('A small story from a very large universe.',H*.52,14,a)
 elif t<12:
  a=ease(6,7,t)*(1-ease(10.5,12,t));label('Even in the deepest dark,',H*.8,18,a);label('something is becoming.',H*.87,18,a)
 elif t<18:
  a=ease(13.4,14.5,t)*(1-ease(16.5,18,t));label('An ending can travel a long way',H*.8,18,a);label('before it becomes a beginning.',H*.87,18,a)
 else:
  a=ease(19,21,t);label('Somewhere, a first sunrise.',H*.2,24,a);label('And a story still unwritten.',H*.3,15,a)
 # Gentle fades, no flash transitions.
 fade=ease(0,.6,t)*(1-ease(23,24,t))
 return Image.fromarray((np.asarray(im)*fade).astype('uint8'))
proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','28','-pix_fmt','yuv420p',str(P/'silent.mp4')],stdin=subprocess.PIPE)
for i in range(FPS*SECONDS): proc.stdin.write(frame(i/FPS).tobytes())
proc.stdin.close();assert proc.wait()==0
frame(9).save(P/'poster.jpg',quality=85)
sr=44100; ts=np.arange(sr*SECONDS)/sr; sig=np.zeros(len(ts))
for start,notes in [(0,[130.81,196,261.63]),(6,[110,164.81,220]),(12,[87.31,130.81,174.61]),(18,[130.81,196,293.66,392])]:
 local=ts-start; env=np.clip(local/2,0,1)*np.clip((8-local)/3,0,1)
 for j,f in enumerate(notes):sig+=.045*env*(np.sin(2*np.pi*f*ts+np.sin(ts*.3)*.3)+.2*np.sin(2*np.pi*f*2*ts))
sig*=np.clip(ts/2,0,1)*np.clip((SECONDS-ts)/2,0,1)
stereo=np.stack([sig,np.roll(sig,330)],axis=1)
with wave.open(str(P/'score.wav'),'wb') as wav:
 wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(sr);wav.writeframes((stereo*32767).astype('<i2').tobytes())
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(P/'silent.mp4'),'-i',str(P/'score.wav'),'-c:v','copy','-c:a','aac','-b:a','96k','-shortest','-movflags','+faststart',str(P/'last-light.mp4')],check=True)
print('Rendered', (P/'last-light.mp4').stat().st_size,'bytes')
