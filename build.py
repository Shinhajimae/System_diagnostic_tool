from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os,subprocess,sys

root=Path(__file__).resolve().parent
work=root/'.build';work.mkdir(exist_ok=True)
temp=work/'temp';temp.mkdir(exist_ok=True)

def build(job):
    name,script,console=job
    env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp),PYINSTALLER_CONFIG_DIR=str(work/'cache'/name))
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--console' if console else '--noconsole','--name',name,'--icon',str(root/'terminal.ico'),'--add-data',str(root/'terminal.ico')+';.', '--manifest',str(root/'app.manifest'),'--collect-all','HardwareMonitor','--hidden-import','clr','--workpath',str(work/name),'--specpath',str(work/'specs'),'--distpath',str(root),str(root/script)]
    with (work/(name+'.log')).open('w') as log:
        result=subprocess.run(args,env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT)
    print(name+(': built' if result.returncode==0 else ': FAILED; see .build/'+name+'.log'),flush=True)
    return result.returncode

with ThreadPoolExecutor(max_workers=3) as pool:
    results=list(pool.map(build,[('Diagnostic','diagnostic.py',True),('Sensors','sensors.py',False)]))
sys.exit(1 if any(results) else 0)
