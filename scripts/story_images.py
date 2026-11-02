"""Story mode: queue many scene images on the user's TST Auto Generate Image app (MCP server `auto-image`,
http://127.0.0.1:47100/mcp) in one run, instead of one agent tool call per image (docs/STORY_MODE.md).

  PY scripts/story_images.py "input/<story>" PROMPTS.jsonl [PROMPTS2.jsonl ...] [--from 11] [--to 488] [--wait]

Prompt lines: {"n": 12, "refs": ["Khue"], "prompt": "..."}; refs resolve to input/<story>/refs/<Name>.png.
Each image goes to input/<story>/_gen/NNN/ (the app adds its own subfolders); then copy the newest file there to
input/<story>/NNN.png (--collect). Job ids are kept in input/<story>/_gen/jobs.json, so a rerun skips queued/done
numbers and retries errors. The bearer token is read from Claude Code's MCP config at run time and never printed."""
import argparse, json, os, shutil, sys, time, urllib.request
from pathlib import Path

URL = 'http://127.0.0.1:47100/mcp'


def token():
    cfg = json.loads(Path(os.path.expanduser('~/.claude.json')).read_text(encoding='utf-8'))
    stack = [cfg]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            srv = o.get('auto-image')
            if isinstance(srv, dict) and (srv.get('headers') or {}).get('Authorization'):
                return srv['headers']['Authorization']
            stack.extend(o.values())
    sys.exit('auto-image MCP server not found in ~/.claude.json (add it to Claude Code first)')


class MCP:
    def __init__(self):
        self.auth, self.sid, self.n = token(), None, 0
        self.call('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                 'clientInfo': {'name': 'story_images', 'version': '1'}})
        self.post({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def post(self, body):
        h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'Authorization': self.auth}
        if self.sid:
            h['Mcp-Session-Id'] = self.sid
        req = urllib.request.Request(URL, json.dumps(body).encode(), h, method='POST')
        with urllib.request.urlopen(req, timeout=120) as r:
            self.sid = r.headers.get('Mcp-Session-Id') or self.sid
            raw = r.read().decode('utf-8', 'replace')
        if not raw.strip():
            return None
        if raw.lstrip().startswith('{'):
            return json.loads(raw)
        data = [l[5:].strip() for l in raw.splitlines() if l.startswith('data:')]
        return json.loads(data[-1]) if data else None

    def call(self, method, params):
        self.n += 1
        res = self.post({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params})
        if res and res.get('error'):
            raise RuntimeError(res['error'])
        return (res or {}).get('result')

    def tool(self, name, args):
        r = self.call('tools/call', {'name': name, 'arguments': args})
        txt = ''.join(c.get('text', '') for c in (r or {}).get('content', []) if c.get('type') == 'text')
        if (r or {}).get('isError'):
            raise RuntimeError(txt[:300])
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            return txt


def collect(story, nums):
    got = []
    for n in nums:
        g = story / '_gen' / f'{n:03}'
        src = sorted(g.rglob('*.png'), key=lambda p: p.stat().st_mtime) if g.exists() else []
        if src:
            dst = story / f'{n:03}.png'
            if not dst.exists() or dst.stat().st_size != src[-1].stat().st_size:
                shutil.copy2(src[-1], dst)
            got.append(n)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('story'); ap.add_argument('prompts', nargs='+')
    ap.add_argument('--from', dest='a', type=int, default=1); ap.add_argument('--to', dest='b', type=int, default=99999)
    ap.add_argument('--wait', action='store_true', help='poll until all done (stall check 15 min, hard cap 8 h), then collect')
    ap.add_argument('--collect', action='store_true', help='only copy finished images to NNN.png')
    a = ap.parse_args()
    story = Path(a.story).resolve()
    rows = [json.loads(l) for f in a.prompts for l in Path(f).read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    rows = sorted([r for r in rows if a.a <= r['n'] <= a.b], key=lambda r: r['n'])
    nums = [r['n'] for r in rows]
    if a.collect:
        got = collect(story, nums); print(f'collected {len(got)}/{len(nums)}; missing {sorted(set(nums) - set(got))}'); return
    jf = story / '_gen' / 'jobs.json'; jf.parent.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(jf.read_text(encoding='utf-8')) if jf.exists() else {}
    m = MCP()
    use = m.tool('get_usage', {}); print('usage:', use)
    done_imgs = set(collect(story, nums))
    queued = 0
    for r in rows:
        key = str(r['n'])
        if r['n'] in done_imgs or key in jobs and jobs[key].get('status') not in ('error', None):
            continue
        refs = [str(story / 'refs' / f'{x}.png') for x in r.get('refs') or []]
        miss = [x for x in refs if not Path(x).exists()]
        if miss:
            sys.exit(f'n={r["n"]}: missing reference {miss}')
        args = {'prompt': r['prompt'], 'aspect_ratio': '16:9', 'output_folder': str(story / '_gen' / f'{r["n"]:03}')}
        if refs:
            args['reference_images'] = refs
        j = m.tool('generate_image', args)
        jobs[key] = {'job_id': j['job_id'], 'status': j.get('status', 'pending')}; queued += 1
        jf.write_text(json.dumps(jobs, indent=1), encoding='utf-8')
    print(f'queued {queued}; {len(done_imgs)} already have images')
    if not a.wait:
        return
    t0, last_change, last_done = time.time(), time.time(), -1
    while True:
        ids = [v['job_id'] for k, v in jobs.items() if int(k) in nums and v.get('status') not in ('done', 'error')]
        for i in range(0, len(ids), 50):
            for s in m.tool('get_jobs', {'job_ids': ids[i:i + 50]}) or []:
                for k, v in jobs.items():
                    if v['job_id'] == s['job_id']:
                        v['status'] = s['status']
        jf.write_text(json.dumps(jobs, indent=1), encoding='utf-8')
        st = [jobs[str(n)]['status'] for n in nums if str(n) in jobs]
        done, err = st.count('done'), st.count('error')
        print(f'{time.strftime("%H:%M:%S")} done {done}, error {err}, open {len(st) - done - err}', flush=True)
        if done != last_done:
            last_done, last_change = done, time.time()
        if done + err == len(st):
            break
        if time.time() - last_change > 900:
            sys.exit('STALL: no image finished for 15 min (is the app running and its MCP server on?)')
        if time.time() - t0 > 8 * 3600:
            sys.exit('hard timeout 8 h')
        time.sleep(30)
    got = collect(story, nums)
    print(f'collected {len(got)}/{len(nums)}; errors: {[n for n in nums if jobs.get(str(n), {}).get("status") == "error"]}')


if __name__ == '__main__':
    main()
