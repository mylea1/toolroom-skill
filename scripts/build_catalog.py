#!/usr/bin/env python3
"""Discover local projects and render an offline, searchable studio catalog."""
import argparse, plistlib, datetime, hashlib, json, os, re, shlex, subprocess
from pathlib import Path

SKIP = {'.git','node_modules','vendor','vendors','.venv','venv','env','__pycache__','build','dist','target','.next','.cache','.npm','.pnpm-store','Pods','DerivedData','site-packages','Library','coverage','venv311','.venv311','skill-validation-env'}
MARKERS = {'.git','package.json','pyproject.toml','Cargo.toml','go.mod','pubspec.yaml','docker-compose.yml','docker-compose.yaml','compose.yaml','compose.yml','project.godot','*.xcodeproj'}

def git(path, *args):
    try:
        r = subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,timeout=4,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_TERMINAL_PROMPT':'0'})
        return r.stdout.strip() if r.returncode == 0 else ''
    except (OSError,subprocess.TimeoutExpired): return ''

def remote_url(value):
    value = re.sub(r'^git@([^:]+):',r'https://\1/',value.strip())
    value = re.sub(r'^ssh://git@', 'https://', value)
    value = re.sub(r'(https?://)[^/]+@',r'\1',value)
    value = value.split('?')[0].split('#')[0].removesuffix('.git').rstrip('/')
    return value if re.match(r'^https?://[^\s]+$',value) else ''

def read_json(p):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except (OSError,ValueError,UnicodeError): return {}

def describe(path):
    for name in ['README.md','README.zh-CN.md','readme.md','README.txt']:
        p=path/name
        if not p.is_file():continue
        try: lines=p.read_text(errors='replace')[:16000].splitlines()
        except OSError:continue
        for line in lines:
            s=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',line).strip()
            if 18<len(s)<320 and not re.match(r'[#|!<>`\[\-*]',s) and not re.search(r'https?://|password|token|api.key|密码|密钥',s,re.I):
                return s, name
    return '已获取到本地，添加一句介绍方便下次找到。',''

def commands(path, names, package):
    found=[]
    if package and isinstance(package.get('scripts'),dict):
        manager='pnpm' if 'pnpm-lock.yaml' in names else 'yarn' if 'yarn.lock' in names else 'npm'
        for task in ['dev','start','serve','preview']:
            if task in package['scripts']:
                found.append({'label':task,'command':f'cd {shlex.quote(str(path))}\n{manager} run {task}','source':'package.json · scripts.'+task,'kind':'项目配置'})
    for name in sorted(names):
        if name.endswith('.command') or name in ['start.sh','start-web.sh','run.sh','启动本地.command','启动预览.command']:
            found.append({'label':name,'command':f'cd {shlex.quote(str(path))}\n'+('open '+shlex.quote(name) if name.endswith('.command') else 'bash '+shlex.quote(name)), 'source':name,'kind':'现有启动脚本'})
    compose=next((n for n in ['compose.yaml','compose.yml','docker-compose.yml','docker-compose.yaml'] if n in names),None)
    if compose:found.append({'label':'Docker Compose','command':f'cd {shlex.quote(str(path))}\ndocker compose -f {shlex.quote(compose)} up -d','source':compose,'kind':'按配置生成'})
    if not found and 'index.html' in names:
        found.append({'label':'静态预览','command':f'cd {shlex.quote(str(path))}\npython3 -m http.server 8000 --bind 127.0.0.1','source':'index.html','kind':'建议命令，未执行'})
    if path.suffix=='.app':found.append({'label':'打开应用','command':'open '+shlex.quote(str(path)),'source':path.name,'kind':'应用入口'})
    for name in sorted(names):
        if name.endswith('.xcodeproj'):found.append({'label':'Xcode 工程','command':'open '+shlex.quote(str(path/name)),'source':name,'kind':'工程入口'})
    return found

def inspect(path, names):
    package=read_json(path/'package.json'); package=package if isinstance(package,dict) else {}
    repo=remote_url(git(path,'config','--get','remote.origin.url')) if '.git' in names else ''
    head=git(path,'rev-parse','HEAD') if '.git' in names else ''
    branch=git(path,'branch','--show-current') if head else ''
    dirty=bool(git(path,'status','--porcelain','--untracked-files=no')) if head else False
    description,source=describe(path)
    if isinstance(package.get('description'),str) and package['description'].strip():description=package['description'][:320];source='package.json'
    stack=[]
    for marker,label in [('package.json','JavaScript'),('pyproject.toml','Python'),('requirements.txt','Python'),('Cargo.toml','Rust'),('go.mod','Go'),('pubspec.yaml','Flutter'),('index.html','HTML')]:
        if marker in names and label not in stack:stack.append(label)
    if any(n.endswith('.xcodeproj') for n in names):stack.append('iOS')
    if path.suffix=='.app':stack.append('macOS App')
    version=str(package.get('version',''))
    bundle={}
    if path.suffix=='.app':
        try:
            with (path/'Contents/Info.plist').open('rb') as f:bundle=plistlib.load(f)
        except (OSError,ValueError,plistlib.InvalidFileException):pass
        version=str(bundle.get('CFBundleShortVersionString',version))
    identity=repo.lower() or ('bundle:'+bundle['CFBundleIdentifier'] if bundle.get('CFBundleIdentifier') else 'package:'+package['name'] if isinstance(package.get('name'),str) and package['name'] else '')
    return {'identity':identity,'id':hashlib.sha256(str(path).encode()).hexdigest()[:16], 'name':path.stem if path.suffix=='.app' else path.name,'path':str(path),'aliases':[],'repo':repo,'version':version,'commit':head,'branch':branch,'dirty':dirty,'description':description,'descriptionSource':source,'stack':stack,'category':'开发工具','acquired':'已获取','runStatus':'未检查运行状态','modified':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),'commands':commands(path,names,package),'uses':[]}

def discover(roots, max_depth=10):
    projects={}; errors=[]; visited=set(); inspected=0
    def walk(path,depth,parent_project=False):
        nonlocal inspected
        try:
            real=path.resolve()
            if real in projects:
                if str(path)!=str(real) and str(path) not in projects[real]['aliases']:projects[real]['aliases'].append(str(path))
                return
            if real in visited:return
            visited.add(real)
            if depth>max_depth:return
            names=set(os.listdir(real));inspected+=1
            is_project=bool(names & (MARKERS-{'*.xcodeproj'})) or any(n.endswith('.xcodeproj') for n in names) or real.suffix=='.app'
            # Static downloads without a package manifest also count.
            is_project=is_project or ('index.html' in names and any(n.lower().startswith('readme') for n in names))
            if is_project and (not parent_project or '.git' in names or real.suffix=='.app'):
                projects[real]=inspect(real,names)
                if str(path)!=str(real):projects[real]['aliases'].append(str(path))
            if real.suffix=='.app':return
            for name in sorted(names):
                if name in SKIP or name.startswith('.') or name.endswith(('.xcodeproj','.xcworkspace')):continue
                child=real/name
                if child.is_dir():walk(child,depth+1,parent_project or is_project)
        except (OSError,RuntimeError) as exc:errors.append({'path':str(path),'error':type(exc).__name__})
    for root in roots:walk(Path(root).expanduser().absolute(),0)
    return list(projects.values()),{'roots':[str(Path(r).expanduser().absolute()) for r in roots],'directories':inspected,'maxDepth':max_depth,'errors':errors}

def apply_annotations(projects, data):
    for p in projects:
        for a in data.get('projects',[]):
            match=a.get('match',{})
            if not match:continue
            matches=all((p.get(k)==v if k!='name' else p['name'].casefold()==str(v).casefold()) for k,v in match.items() if k in ('name','repo','path'))
            if not any(k in match for k in ('name','repo','path')) or not matches:continue
            for k in ['description','category','uses','runStatus','evidence','displayName']:
                if k in a:p[k]=a[k]
            if a.get('commands'):p['commands']=a['commands']+p['commands']
    groups={}
    for p in projects:
        key=p.get('identity',p['repo'].lower())
        if key:groups.setdefault(key,[]).append(p)
    duplicates=[]
    for repo,items in groups.items():
        if len(items)<2:continue
        commits={p['commit'] for p in items if p['commit']}
        duplicates.append({'repo':items[0]['repo'],'identity':repo,'ids':[p['id'] for p in items],'name':items[0].get('displayName',items[0]['name']),'comparison':'同一提交' if len(commits)==1 and all(p['commit'] for p in items) else '存在不同版本' if len(commits)>1 else '同一项目身份 · 比较版本与位置'})
    workflows=[]
    for w in data.get('workflows',[]):
        steps=[]
        for step in w.get('steps',[]):
            names=step.get('projects',[])
            ids=[p['id'] for p in projects if p['name'] in names or p.get('displayName') in names]
            steps.append({**step,'ids':ids})
        workflows.append({**w,'steps':steps})
    return duplicates,workflows

def render(data, output):
    template=Path(__file__).resolve().parent.parent/'assets/catalog.html'
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(template.read_text().replace('__CATALOG_DATA__',payload),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',action='append',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--annotations');ap.add_argument('--max-depth',type=int,default=10)
    args=ap.parse_args()
    projects,coverage=discover(args.root,args.max_depth)
    annotations=json.loads(Path(args.annotations).read_text(encoding='utf-8')) if args.annotations else {}
    duplicates,workflows=apply_annotations(projects,annotations)
    data={'schemaVersion':1,'generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'projects':projects,'duplicates':duplicates,'workflows':workflows,'coverage':coverage}
    render(data,args.output)
    Path(args.output).with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(json.dumps({'html':str(Path(args.output).resolve()),'projects':len(projects),'duplicates':len(duplicates),'workflows':len(workflows),'readErrors':len(coverage['errors'])},ensure_ascii=False))
if __name__=='__main__':main()
