"""Local material manifests; independent of model and AI asset services."""
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'data/material_library_roots.json'
def roots():
    extra=json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else []
    return [ROOT/'data/materials']+[Path(p) for p in extra]
def add_root(path):
    path=str(Path(path).resolve())
    extra=json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else []
    if path not in extra:
        extra.append(path)
        CONFIG.write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
class Catalog:
    def __init__(self):
        self.items=[]
    def refresh(self):
        result=[];seen=set()
        for root in roots():
            for manifest in sorted(root.rglob('materials.json')):
                if manifest.resolve() in seen: continue
                seen.add(manifest.resolve())
                for index,info in enumerate(json.loads(manifest.read_text(encoding='utf-8-sig'))['list']):
                    texture=str((manifest.parent/info['texture']).resolve()) if info.get('texture') else None
                    key=hashlib.sha256((str(manifest.resolve())+':'+str(index)).encode()).hexdigest()
                    result.append(dict(id=key,kind='material',name=info['name'],description='',path=str(manifest),preview=texture,properties=dict(info,texture_path=texture)))
        self.items=result
        return result
    def search(self,query='',kind=None,limit=None):
        words=query.casefold().split()
        return [a for a in self.items if all(w in a['name'].casefold() for w in words)][:limit]
