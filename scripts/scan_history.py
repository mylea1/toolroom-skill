#!/usr/bin/env python3
"""Read Codex JSONL history into a private, searchable SQLite evidence index."""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

SIGNALS = re.compile(r'部署|安装|配置|启动|搭建|deploy|install|git\s+clone|docker|podman|pipx?|\buv\b|\bnpm\b|\bbrew\b|github\.com|gitlab\.com|MCP', re.I)


def redact(text):
    text = re.sub(r'((?:密码|密钥|令牌)(?:为|是|[:：])\s*)[^\s，,。；;\"}]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)(authorization\s*[:=]\s*[\"\x27]?)(?:bearer\s+)?[^\s\"\x27,}]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|password|secret)\s*[\"\x27]?\s*[:=]\s*[\"\x27]?)[^\s\"\x27,}]+', r'\1[REDACTED]', text)
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]+)\b', '[REDACTED]', text)
    return re.sub(r'(https?://)[^/\s:@]+:[^/\s@]+@', r'\1[REDACTED]@', text)


def flatten(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(filter(None, (flatten(v) for v in value)))
    if isinstance(value, dict):
        return '\n'.join(flatten(value[k]) for k in ('text', 'content', 'output') if k in value)
    return ''


def extract(record):
    p = record.get('payload', {})
    if not isinstance(p, dict):
        return None
    kind = p.get('type', '')
    if record.get('type') == 'event_msg' and kind == 'item_completed':
        item = p.get('item', {})
        if not isinstance(item, dict):
            return None
        item_kind = item.get('type')
        if item_kind in ('UserMessage', 'AgentMessage'):
            return ('user' if item_kind == 'UserMessage' else 'assistant'), flatten(item.get('content', '')), ''
        if item_kind == 'CommandExecution':
            body = {k: item.get(k) for k in ('command','cwd','status','exit_code','aggregated_output','stdout','stderr') if item.get(k) is not None}
            return 'execution', json.dumps(body, ensure_ascii=False), item.get('id', '')
        if item_kind == 'McpToolCall':
            body = {k: item.get(k) for k in ('server','tool','arguments','status','result')}
            return 'mcp_execution', json.dumps(body, ensure_ascii=False), item.get('id', '')
    if record.get('type') == 'response_item':
        if kind in ('message', 'agent_message'):
            role = p.get('role', p.get('author', 'agent'))
            if role in ('system', 'developer'):
                return None
            return role, flatten(p.get('content', '')), p.get('call_id', '')
        if kind in ('function_call', 'custom_tool_call'):
            value = p.get('arguments', p.get('input', ''))
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            return 'call:' + p.get('name', ''), value, p.get('call_id', '')
        if kind in ('function_call_output', 'custom_tool_call_output'):
            value = p.get('output', '')
            return 'result', value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), p.get('call_id', '')
    if record.get('type') == 'event_msg' and kind in ('user_message', 'agent_message'):
        return kind, flatten(p.get('message', '')), ''
    if record.get('type') == 'compacted':
        return 'summary', p.get('message', ''), ''
    return None


def build(args):
    dest = Path(args.db).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit('Index exists; choose a new --db path for a fresh snapshot.')
    old = os.umask(0o077)
    try:
        db = sqlite3.connect(dest)
    finally:
        os.umask(old)
    db.executescript('''CREATE TABLE records(id INTEGER PRIMARY KEY, source TEXT, line INTEGER,
        session TEXT, parent TEXT, stamp TEXT, role TEXT, call_id TEXT, text TEXT,
        fingerprint TEXT, candidate INTEGER);
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT);
        CREATE INDEX session_idx ON records(session);
        CREATE INDEX call_idx ON records(call_id);''')
    coverage = {'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'roots': [], 'files': 0, 'records': 0, 'errors': [], 'unknown_types': {},
                'scope': 'Local accessible files only; cloud, other devices and deleted history not guaranteed.'}
    unknown = collections.Counter()
    seen_files = set()
    sessions = set()
    for root in args.root:
        root = Path(root).expanduser().resolve()
        coverage['roots'].append(str(root))
        if not root.exists():
            coverage['errors'].append({'source': str(root), 'error': 'root missing'})
        for folder in ('sessions', 'archived_sessions'):
            for path in sorted((root / folder).rglob('*.jsonl')):
                path = path.resolve()
                if path in seen_files:
                    continue
                seen_files.add(path)
                coverage['files'] += 1
                session, parent = path.stem, ''
                try:
                    with path.open(encoding='utf-8') as stream:
                        for line_no, line in enumerate(stream, 1):
                            try:
                                record = json.loads(line)
                                if not isinstance(record, dict):
                                    raise ValueError('non-object record')
                                p = record.get('payload', {})
                                if record.get('type') == 'session_meta' and isinstance(p, dict):
                                    session = p.get('id') or p.get('session_id') or session
                                    parent = p.get('forked_from_id') or p.get('parent_thread_id') or ''
                                item = extract(record)
                                if not item:
                                    unknown[str(record.get('type')) + '/' + str(p.get('type') if isinstance(p, dict) else '')] += 1
                                    continue
                                role, body, call = item
                                if not body:
                                    continue
                                body = redact(body)
                                fp = hashlib.sha256((role + '\0' + body).encode()).hexdigest()
                                db.execute('INSERT INTO records VALUES(NULL,?,?,?,?,?,?,?,?,?,?)',
                                    (str(path), line_no, session, parent, record.get('timestamp', ''), role,
                                     call, body, fp, int(bool(SIGNALS.search(body)))))
                                sessions.add(session)
                                coverage['records'] += 1
                            except (ValueError, TypeError, AttributeError) as exc:
                                coverage['errors'].append({'source': str(path), 'line': line_no, 'error': type(exc).__name__})
                except (OSError, UnicodeError) as exc:
                    coverage['errors'].append({'source': str(path), 'error': type(exc).__name__})
    coverage['sessions'] = len(sessions)
    coverage['unknown_types'] = dict(unknown)
    db.execute('INSERT INTO metadata VALUES(?,?)', ('coverage', json.dumps(coverage, ensure_ascii=False)))
    db.commit()
    db.close()
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


def query(args):
    db = sqlite3.connect(Path(args.db).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    if args.action == 'coverage':
        print(db.execute("SELECT value FROM metadata WHERE key='coverage'").fetchone()[0])
        return
    conditions, values = [], []
    if args.action == 'candidates':
        conditions.append('candidate=1')
    if args.session:
        conditions.append('session=?'); values.append(args.session)
    if args.term:
        conditions.append('(' + ' OR '.join('instr(lower(text),lower(?))>0' for _ in args.term) + ')')
        values.extend(args.term)
    if args.call_id:
        conditions.append('call_id=?'); values.append(args.call_id)
    if args.source:
        conditions.append('source=?'); values.append(args.source)
    if args.line:
        conditions.append('line BETWEEN ? AND ?'); values.extend([max(1,args.line-args.context), args.line+args.context])
    where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
    total = db.execute('SELECT count(*) FROM records' + where, values).fetchone()[0]
    rows = db.execute('SELECT * FROM records' + where + ' ORDER BY source,line LIMIT ? OFFSET ?', values + [args.limit, args.offset])
    print(json.dumps({'total':total, 'offset':args.offset, 'limit':args.limit, 'next_offset':args.offset+args.limit if args.offset+args.limit<total else None}))
    for row in rows:
        item = dict(row)
        item['truncated'] = len(item['text']) > args.max_chars if args.max_chars else False
        if args.max_chars:
            item['text'] = item['text'][:args.max_chars]
        print(json.dumps(item, ensure_ascii=False))
    db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'coverage', 'candidates', 'search', 'context'])
    parser.add_argument('--db', required=True)
    parser.add_argument('--root', action='append')
    parser.add_argument('--term', action='append', default=[])
    parser.add_argument('--session')
    parser.add_argument('--call-id')
    parser.add_argument('--source')
    parser.add_argument('--line', type=int)
    parser.add_argument('--context', type=int, default=12)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--max-chars', type=int, default=2000, help='0 returns full evidence')
    args = parser.parse_args()
    if args.limit < 1 or args.offset < 0 or args.max_chars < 0 or args.context < 0:
        parser.error('Invalid pagination or size')
    if args.action == 'context' and not (args.source and args.line):
        parser.error('context requires --source and --line')
    args.root = args.root or [os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))]
    build(args) if args.action == 'build' else query(args)


if __name__ == '__main__':
    main()
