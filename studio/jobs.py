"""Background job runner (started by the studio server or the MCP server; status in render/studio/jobs/<id>.json).

  PY studio/jobs.py <project> <job-id>
"""
import json, os, sys, time, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core as C  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    proj = C.Project(sys.argv[1]); jid = sys.argv[2]
    path = proj.work / 'jobs' / f'{jid}.json'
    st = json.loads(path.read_text(encoding='utf-8'))
    st.update(status='running', pid=os.getpid())
    real = sys.stdout

    def save():
        tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8'); os.replace(tmp, path)

    def log(msg):
        msg = str(msg).rstrip()
        if not msg:
            return
        real.write(msg + '\n'); real.flush()  # the job's .log file
        if msg.lstrip().startswith('frame ') and '/' in msg:  # render.picture progress "  frame i/n"
            i, n = msg.split()[1].split('/'); st['progress'] = round(int(i) / max(1, int(n)), 3)
            if st['log'] and st['log'][-1].lstrip().startswith('frame '):
                st['log'][-1] = msg; save(); return
        st['log'] = (st['log'] + [f'{time.strftime("%H:%M:%S")} {msg}'])[-60:]; save()

    class Tee:  # render.picture prints its progress: route it into the job log
        def write(self, s):
            for line in s.split('\n'):
                log(line)
        def flush(self):
            pass

    save()
    sys.stdout = Tee()
    try:
        a = st['args']
        if st['kind'] == 'preview':
            st['result'] = C.preview(proj, float(a['t0']), float(a['t1']), a.get('mode', 'auto'), log)
        elif st['kind'] == 'export':
            lk = proj.work / 'export.lock'
            fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
            try:
                st['result'] = C.export(proj, log)
            finally:
                lk.unlink(missing_ok=True)
        else:
            raise ValueError(f'unknown job kind {st["kind"]}')
        st['status'] = 'done'; st['progress'] = 1.0
    except FileExistsError:
        st['status'] = 'error'; st['error'] = 'another export is running (render/studio/export.lock)'
    except Exception as e:  # noqa: BLE001 - the job file is the only place the user sees errors
        st['status'] = 'error'; st['error'] = f'{type(e).__name__}: {e}'
        st['log'] = (st['log'] + traceback.format_exc().strip().split('\n')[-6:])[-60:]
    finally:
        sys.stdout = real
        st['ended'] = time.strftime('%Y-%m-%d %H:%M:%S'); save()


if __name__ == '__main__':
    main()
