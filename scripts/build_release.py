"""Run only after the serialized packaging resource is granted."""
import hashlib
import importlib.metadata as md
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

repo=Path(__file__).resolve().parent.parent
os.chdir(repo)
if os.name!='nt' or sys.maxsize<=2**32:raise SystemExit('Build requires Windows x64 Python')
if shutil.disk_usage(repo).free<8*1024**3:raise SystemExit('Preserve 8 GiB build reserve')
if subprocess.check_output(['git','status','--porcelain'],text=True).strip():raise SystemExit('Commit source before packaging')
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
version='0.1.0-preview.3'
info={'source_commit':commit,'version':version,'signing':'unsigned','build':'local Windows 11 x64 / Python '+sys.version.split()[0],'validation_workflow':'https://github.com/mastodonsharkgirl/clearspace/actions/workflows/windows-tests.yml'}
(repo/'clearspace/build_info.json').write_text(json.dumps(info,indent=2))
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','Clearspace.spec'],check=True)
target=repo/'dist/Clearspace'
for name in ['START_HERE.txt','LICENSE','README.md','MODEL_MANIFEST.json']:shutil.copy2(repo/name,target/name)
licenses=target/'licenses';licenses.mkdir(exist_ok=True)
components=[]
for d in md.distributions():
    name=d.metadata['Name'];component={'name':name,'version':d.version,'purl':f'pkg:pypi/{name.lower()}@{d.version}','scope':'build environment; includes test-only dependencies excluded from binary'}
    components.append(component)
    for f in d.files or []:
        if any(x in str(f).lower() for x in ('license','copying','notice')) and Path(str(f)).suffix.lower() not in {'.py','.pyc','.exe','.dll'}:
            src=Path(d.locate_file(f))
            if src.is_file() and src.stat().st_size<500000:
                dest=licenses/name/str(f).replace('..','_').replace('/','_').replace('\\','_');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
for path in [Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'tcl/tcl8.6/license.terms',Path(sys.base_prefix)/'tcl/tk8.6/license.terms']:
    if path.exists():shutil.copy2(path,licenses/(path.parent.name+'-'+path.name))
for package in ['react','react-dom','scheduler']:
    p=repo/'node_modules'/package
    pkg=json.loads((p/'package.json').read_text());components.append({'name':package,'version':pkg['version'],'purl':f'pkg:npm/{package}@{pkg["version"]}','scope':'compiled UI'})
    shutil.copy2(p/'LICENSE',licenses/(package+'-LICENSE'))
sbom={'format':'Clearspace dependency inventory v1','source_commit':commit,'python':sys.version.split()[0],'components':components,'note':'Not a vulnerability attestation. PyInstaller module list is in build artifacts; licenses include build/test dependencies for transparency.'}
(target/'SBOM.json').write_text(json.dumps(sbom,indent=2))
(target/'BUILD_INFO.json').write_text(json.dumps(info,indent=2))
(target/'THIRD_PARTY_NOTICES.txt').write_text('Clearspace includes CPython, Tcl/Tk, FastAPI/Starlette/Pydantic/Uvicorn and their dependencies, plus React. License texts are in licenses/. PyInstaller bootloader has its distribution exception. Build-only and test dependencies are listed separately by scope in SBOM.json. No model weights are bundled.\n')
out=repo/'outputs'/version;out.mkdir(parents=True,exist_ok=True)
archive=out/f'Clearspace-{version}-windows-x64.zip'
if archive.exists():raise SystemExit('Release archive already exists; choose a new version')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in target.rglob('*'):
        if p.is_file():z.write(p,Path('Clearspace')/p.relative_to(target))
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
manifest=dict(info,archive=archive.name,sha256=sha,download_bytes=archive.stat().st_size,extracted_bytes=sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),platform='Windows 11 x64',acceptance='PREVIEW: clean standard-user browser download/Extract all/launch acceptance pending',provenance='Local build record; no signed build attestation',models=[])
(out/'release-manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'SHA256SUMS.txt').write_text(f'{sha}  {archive.name}\n')
for name in ['SBOM.json','THIRD_PARTY_NOTICES.txt']:shutil.copy2(target/name,out/name)
print(json.dumps(manifest,indent=2))
