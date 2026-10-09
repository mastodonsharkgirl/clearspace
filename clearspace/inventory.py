import json
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from .metadata import metadata, now, safe_local, volume_space, pinned_directory, canonical_root
from .policy import classify


def normalize_roots(roots):
    paths=[p.strip().strip('"') for p in roots]
    paths=[p+'\\' if re.fullmatch(r'[A-Za-z]:',p) else p for p in paths]
    if any(not os.path.isabs(p) for p in paths):
        raise ValueError('Paste a full folder path, or choose a drive such as C:\\')
    selected = sorted({canonical_root(p) for p in paths}, key=lambda p: (len(p), p.lower()))
    result = []
    identities = set()
    for p in selected:
        s = os.stat(p)
        identity = (s.st_dev, s.st_ino) if s.st_ino else ('path',os.path.normcase(p))
        if identity in identities or any(os.path.commonpath([p, r]).lower() == r.lower() for r in result if Path(p).anchor.lower() == Path(r).anchor.lower()): continue
        if not os.path.isdir(p): raise ValueError('Select folders, not files')
        result.append(p); identities.add(identity)
    if not result: raise ValueError('Choose at least one local folder')
    return result


class Inventory:
    def __init__(self, data, max_items=500000, budget=256*1024**2, reserve=512*1024**2, adapter=metadata):
        self.data = Path(data).absolute(); self.data.mkdir(parents=True, exist_ok=True)
        self.db = self.data / 'inventory.sqlite'
        self.max_items, self.budget, self.reserve, self.adapter = max_items, budget, reserve, adapter
        self.lock = threading.Lock()
        self._report_lock=threading.Lock();self._cached_report=None;self._revision=0
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY, path TEXT, kind TEXT, category TEXT, allocated INTEGER, logical INTEGER, identity TEXT, body TEXT);
            CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY, path TEXT, volume TEXT);
            CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT);
            CREATE TABLE IF NOT EXISTS marks(path TEXT PRIMARY KEY, value TEXT);
            CREATE INDEX IF NOT EXISTS by_allocation ON entries(allocated DESC);
            CREATE INDEX IF NOT EXISTS by_identity ON entries(identity);''')
            c.execute('INSERT OR IGNORE INTO state VALUES(1,?)', (json.dumps(dict(status='empty', items=0, roots=[], gaps=0)),))

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=DELETE'); c.execute('PRAGMA temp_store=MEMORY'); c.execute('PRAGMA cache_size=-4096')
        # Reserve half for SQLite rollback journal; committed DB plus journal stay bounded.
        c.execute(f'PRAGMA max_page_count={max(64, self.budget // 2 // 4096)}')
        try:
            with c: yield c
        finally: c.close()

    def state(self):
        with self.connect() as c: return json.loads(c.execute('SELECT body FROM state').fetchone()[0])

    def save_state(self, c, state):
        c.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(state),)); c.commit()

    def preflight(self):
        return dict(data_location=str(self.data), available=volume_space(str(self.data))['available'], budget=str(self.budget), reserve=str(self.reserve), max_items=self.max_items)

    def scan(self, requested, cancel, protected=()):
        self._checks=0
        roots = normalize_roots(requested)
        protected = [canonical_root(x) for x in protected]
        state = dict(scan_id=str(uuid.uuid4()), started=now(), finished=None, requested_roots=requested, roots=roots, protected=protected, status='scanning', items=0, gaps=0, reason=None, before=[], after=[], streams='Named NTFS streams excluded; allocation covers default streams only.')
        for root in roots:
            v = volume_space(root)
            if v['volume'] not in [x['volume'] for x in state['before']]: state['before'].append(dict(v, root=root))
        with self.connect() as c:
            c.execute('DELETE FROM entries'); c.execute('DELETE FROM queue')
            for root in roots: c.execute('INSERT INTO queue(path,volume) VALUES(?,?)', (root, str(os.stat(root).st_dev)))
            self.save_state(c, state)
            try:
                while True:
                    if cancel.is_set(): state.update(status='cancelled', reason='Cancelled by user; partial inventory retained.'); break
                    q = c.execute('SELECT * FROM queue ORDER BY id LIMIT 1').fetchone()
                    if not q: state['status'] = 'partial' if state['gaps'] else 'complete'; break
                    c.execute('DELETE FROM queue WHERE id=?', (q['id'],))
                    if not self.room(c, state): break
                    path = q['path']
                    if Path(path) == self.data or self.data in Path(path).parents:
                        self.record_error(c, state, path, 'app-data-excluded'); continue
                    try:
                        # Revalidate ancestors before enumeration, without resolving into reparse targets.
                        safe_local(str(Path(path).parent))
                        m = self.adapter(path)
                        self.record(c, state, m, protected)
                        if m['reparse'] or m['cloud'] != 'ordinary-local': state['gaps'] += 1; continue
                        if m['kind'] != 'directory': continue
                        if m['volume'] != q['volume']:
                            state['gaps'] += 1; continue
                        safe_local(path)
                        with pinned_directory(path), os.scandir(path) as entries:
                            for entry in entries:
                                if cancel.is_set(): break
                                if not self.room(c, state): break
                                try:
                                    child = self.adapter(entry.path)
                                    if child['kind'] == 'directory' and not child['reparse'] and child['cloud'] == 'ordinary-local':
                                        c.execute('INSERT INTO queue(path,volume) VALUES(?,?)', (entry.path, q['volume']))
                                    else:
                                        self.record(c, state, child, protected)
                                        if child['reparse'] or child['cloud'] != 'ordinary-local': state['gaps'] += 1
                                except OSError as e: self.record_error(c, state, entry.path, f'error-{getattr(e,"winerror",None) or e.errno}')
                        if state['status'] == 'partial': break
                    except (OSError, ValueError) as e:
                        self.record_error(c, state, path, f'coverage-{getattr(e,"winerror",None) or getattr(e,"errno",None) or "reparse"}')
                    self.save_state(c, state)
            except sqlite3.Error:
                c.rollback(); state.update(status='partial', reason='Inventory storage limit or database error; committed results retained.')
            state['items'] = c.execute('SELECT COUNT(*) FROM entries').fetchone()[0]
            state['finished'] = now(); c.execute('DELETE FROM queue'); self.save_state(c, state)

    def room(self, c, state):
        if state['items'] >= self.max_items:
            state.update(status='partial', reason='Item limit reached. Narrow your selected scope.'); return False
        self._checks=getattr(self,'_checks',0)+1
        if self._checks % 64 == 1:
            c.commit()
            pages = c.execute('PRAGMA page_count').fetchone()[0]
            queued=c.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
            if queued+state['items']>=self.max_items or pages*4096 > self.budget//2 - 1024*1024 or int(volume_space(str(self.data))['available']) < self.reserve + self.budget//2:
                state.update(status='partial', reason='Inventory budget or free-space reserve reached.'); return False
            self.save_state(c, state)
        return True

    def fail(self):
        state=self.state(); state.update(status='partial',reason='Scan could not continue. A selected folder may have moved or access changed.',finished=now())
        with self.connect() as c: self.save_state(c,state)

    def preparing(self,roots):
        state=self.state();state.update(scan_id=str(uuid.uuid4()),status='scanning',reason='Preparing selected scope; prior rows remain until enumeration starts.',started=now(),requested_roots=roots)
        with self.connect() as c:self.save_state(c,state)

    def record(self, c, state, m, protected):
        category, reason, protect, guidance = classify(m, protected)
        m.update(category=category, reason=reason, protected=protect, guidance=guidance, stream_coverage='default-only')
        c.execute('INSERT INTO entries(path,kind,category,allocated,logical,identity,body) VALUES(?,?,?,?,?,?,?)', (m['path'], m['kind'], category, m['allocated'], m['logical'], m['identity'], json.dumps(m)))
        state['items'] += 1

    def record_error(self, c, state, path, error):
        m = dict(path=path, parent=str(Path(path).parent), kind='error', logical=0, allocated=None, identity=None, volume=None, modified_ns=None, links=None, attributes=None, reparse=False, reparse_tag=None, cloud='unknown', allocation_status='unknown', error=error)
        self.record(c, state, m, ()); state['gaps'] += 1

    def report(self):
        with self._report_lock:
            state=self.state()
            key=(json.dumps(state,sort_keys=True),self._revision)
            if self._cached_report and self._cached_report[0]==key:return self._cached_report[1]
            result=self._report()
            self._cached_report=(key,result)
            return result

    def _report(self):
        state = self.state(); logical = allocated = reviewable = unknown = shared = 0; categories = {}; seen = set()
        with self.connect() as c:
            for row in c.execute('SELECT e.*,m.value AS mark FROM entries e LEFT JOIN marks m ON e.path=m.path'):
                m = json.loads(row['body'])
                if m['kind'] != 'file': continue
                logical += m['logical']
                if m['allocated'] is None: unknown += 1; continue
                key = m['identity'] or f"path:{m['path']}"
                if key in seen: continue
                seen.add(key); allocated += m['allocated']
                categories[m['category']] = categories.get(m['category'], 0) + m['allocated']
                if m['links'] > 1: shared += m['allocated']
                if not m['protected'] and m['links'] == 1 and row['mark'] != 'keep': reviewable += m['allocated']
        return dict(state, logical=str(logical), allocated=str(allocated), reviewable=str(reviewable), shared=str(shared), unknown_allocation=unknown, categories={k:str(v) for k,v in categories.items()}, potential_recoverable=None,allocation_scope='Known file default-stream allocation only; directory metadata, named streams and NTFS overhead excluded.')

    def entries(self, offset=0, limit=50, sort='allocated', direction='desc', category=None):
        sort = {'allocated':'e.allocated','logical':'e.logical','path':'e.path'}.get(sort, 'e.allocated')
        direction = 'ASC' if direction == 'asc' else 'DESC'
        where = 'WHERE e.category=?' if category else ''
        args = [category] if category else []
        with self.connect() as c:
            rows = c.execute(f'SELECT e.*,m.value AS mark FROM entries e LEFT JOIN marks m ON e.path=m.path {where} ORDER BY {sort} {direction},e.id LIMIT ? OFFSET ?', (*args, limit, offset)).fetchall()
            total = c.execute(f'SELECT COUNT(*) FROM entries e {where}', args).fetchone()[0]
        entries=[]
        for row in rows:
            m=json.loads(row['body']); m.update(id=row['id'],mark=row['mark'] or 'review')
            for k in ['logical','allocated']: m[k] = str(m[k]) if m[k] is not None else None
            entries.append(m)
        return dict(entries=entries, total=total)

    def entry(self, id):
        with self.connect() as c: row=c.execute('SELECT body FROM entries WHERE id=?',(id,)).fetchone()
        if not row: raise ValueError('Inventory item not found')
        return json.loads(row[0])

    def review_entry(self,id):
        with self.connect() as c:
            row=c.execute('SELECT e.body,m.value AS mark FROM entries e LEFT JOIN marks m ON e.path=m.path WHERE e.id=?',(id,)).fetchone()
        if not row: raise ValueError('Inventory item not found; refresh this view')
        result=json.loads(row['body']); result.update(id=id,mark=row['mark'] or 'review')
        for key in ('logical','allocated'):
            if result[key] is not None: result[key]=str(result[key])
        return result

    def browse(self, path='', offset=0, limit=50):
        """Aggregate only recorded metadata. Navigation never touches the disk."""
        state=self.state(); roots=state.get('roots',[])
        if not roots: return dict(path='',parent=None,roots=[],entries=[],total=0)
        args=[]
        if path:
            with self.connect() as c:
                row=c.execute('SELECT body FROM entries WHERE path=? COLLATE NOCASE AND kind=\'directory\' LIMIT 1',(path,)).fetchone()
            if not row: raise ValueError('Choose a scanned folder from this inventory')
            item=json.loads(row[0]); path=item['path']
            if item['reparse'] or item['cloud']!='ordinary-local': raise ValueError('This folder was excluded from enumeration')
            if not any(path.lower()==r.lower() or path.lower().startswith(r.rstrip('\\/') .lower()+os.sep) for r in roots): raise ValueError('Folder is outside this inventory')
            prefix=path.rstrip('\\/')+os.sep
            # First segment beneath this directory identifies each immediate child.
            relative=f'substr(path,{len(prefix)+1})'
            bucket=f"? || CASE WHEN instr({relative},?)>0 THEN substr({relative},1,instr({relative},?)-1) ELSE {relative} END"
            where='substr(path,1,?)=? COLLATE NOCASE AND length(path)>?'
            args=[prefix,os.sep,os.sep,len(prefix),prefix,len(prefix)]
        else:
            cases=[]; conditions=[]
            for root in roots:
                prefix=root.rstrip('\\/')+os.sep
                condition='(path=? COLLATE NOCASE OR substr(path,1,?)=? COLLATE NOCASE)'
                cases.append(f'WHEN {condition} THEN ?')
                args.extend([root,len(prefix),prefix,root])
                conditions.append(condition)
            bucket='CASE '+' '.join(cases)+' END'
            where=' OR '.join(conditions)
            for root in roots:
                prefix=root.rstrip('\\/')+os.sep
                args.extend([root,len(prefix),prefix])
        query=f'''WITH grouped AS (SELECT id,path,kind,allocated,logical,identity,body,{bucket} AS bucket FROM entries WHERE {where}),
            totals AS (SELECT bucket,MIN(CASE WHEN path=bucket THEN id END) AS entry_id,SUM(CASE WHEN kind='file' THEN logical ELSE 0 END) AS logical,
                SUM(kind='file') AS files,SUM(kind='file' AND allocated IS NULL) AS unknown,
                SUM(kind='error' OR json_extract(body,'$.reparse')=1 OR json_extract(body,'$.cloud')!='ordinary-local') AS gaps
                FROM grouped GROUP BY bucket),
            known AS (SELECT bucket,SUM(allocated) AS allocated FROM
                (SELECT bucket,COALESCE(identity,path),MAX(allocated) AS allocated FROM grouped WHERE kind='file' AND allocated IS NOT NULL GROUP BY bucket,COALESCE(identity,path)) GROUP BY bucket)
            SELECT t.*,COALESCE(k.allocated,0) AS allocated,e.id,e.kind,e.body
            FROM totals t LEFT JOIN known k ON k.bucket=t.bucket LEFT JOIN entries e ON e.id=t.entry_id
            ORDER BY allocated DESC,t.bucket LIMIT ? OFFSET ?'''
        with self.connect() as c:
            rows=c.execute(query,(*args,limit+1,offset)).fetchall()
        result=[]
        for row in rows[:limit]:
            body=json.loads(row['body']) if row['body'] else {}
            allocation=None if row['kind'] in ('file','error') and body.get('allocated') is None else str(row['allocated'])
            result.append(dict(id=row['id'],path=row['bucket'],kind=row['kind'] or 'directory',allocated=allocation,logical=str(row['logical']),files=row['files'],unknown=row['unknown'],gaps=row['gaps'],navigable=row['kind']=='directory' and not body.get('reparse') and body.get('cloud')=='ordinary-local'))
        parent='' if not path or path.lower() in [r.lower() for r in roots] else str(Path(path).parent)
        return dict(path=path,parent=parent,roots=roots,entries=result,offset=offset,has_more=len(rows)>limit,status=state['status'])

    def mark(self, id, value):
        if value not in {'keep','later','review'}: raise ValueError('Invalid review state')
        m=self.entry(id)
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO marks VALUES(?,?)',(m['path'],value))
        self._revision+=1

    def remeasure(self):
        state=self.state(); state['after']=[dict(volume_space(x['root']),root=x['root']) for x in state.get('before',[])]
        with self.connect() as c: self.save_state(c,state)
        return state['after']
