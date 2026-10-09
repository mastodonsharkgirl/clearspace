import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from .metadata import metadata, now, safe_local, volume_space
from .policy import classify


def normalize_roots(roots):
    selected = sorted({safe_local(p) for p in roots}, key=lambda p: (len(p), p.lower()))
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
        c.execute(f'PRAGMA max_page_count={max(64, self.budget // 4096)}')
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
        roots = normalize_roots(requested)
        protected = [safe_local(x) for x in protected]
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
                        with os.scandir(path) as entries:
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
        if state['items'] % 64 == 0:
            c.commit()
            pages = c.execute('PRAGMA page_count').fetchone()[0]
            if pages*4096 > self.budget - 1024*1024 or int(volume_space(str(self.data))['available']) < self.reserve + 2*1024*1024:
                state.update(status='partial', reason='Inventory budget or free-space reserve reached.'); return False
            self.save_state(c, state)
        return True

    def record(self, c, state, m, protected):
        category, reason, protect, guidance = classify(m, protected)
        m.update(category=category, reason=reason, protected=protect, guidance=guidance, stream_coverage='default-only')
        c.execute('INSERT INTO entries(path,kind,category,allocated,logical,identity,body) VALUES(?,?,?,?,?,?,?)', (m['path'], m['kind'], category, m['allocated'], m['logical'], m['identity'], json.dumps(m)))
        state['items'] += 1

    def record_error(self, c, state, path, error):
        m = dict(path=path, parent=str(Path(path).parent), kind='error', logical=0, allocated=None, identity=None, volume=None, modified_ns=None, links=None, attributes=None, reparse=False, reparse_tag=None, cloud='unknown', allocation_status='unknown', error=error)
        self.record(c, state, m, ()); state['gaps'] += 1

    def report(self):
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

    def mark(self, id, value):
        if value not in {'keep','later','review'}: raise ValueError('Invalid review state')
        m=self.entry(id)
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO marks VALUES(?,?)',(m['path'],value))

    def remeasure(self):
        state=self.state(); state['after']=[dict(volume_space(x['root']),root=x['root']) for x in state.get('before',[])]
        with self.connect() as c: self.save_state(c,state)
        return state['after']
