import os 
import shutil
hp=os.path.expanduser('~')
dp=os.path.join(hp,'Downloads')
folders={
    'Images':['.jpg','.jpeg','.png','.gif','.bmp','.tiff'],
    'Documents':['.pdf','.doc','.docx','.txt','.xls','.xlsx','.ppt','.pptx'],
    'Music':['.mp3','.wav','.aac','.flac','.ogg'],
    'Archives':['.zip','.rar','.tar','.gz','.7z'],
    'Scripts':['.py','.js','.sh','.bat','.pl'],
    'EXEL':['.ods','odt'],
    'iTunes':['.dmg'],
    'Others':[]
}   
for fn in os.listdir(dp):
    fp=os.path.join(dp,fn)
    if os.path.isfile(fp)==0:
        continue
    a,ext=os.path.splitext(fn)
    ext=ext.lower()
    moved=0
    for fn,el in folders.items():
        if ext in el:
            tf=os.path.join(dp,fn)
            os.makedirs(tf,exist_ok=1)
            tp=os.path.join(tf,fn)
            shutil.move(fp,tp)
            moved=1
            break
