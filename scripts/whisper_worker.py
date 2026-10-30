"""Whisper worker process (started by whisper_align.WhisperWorker; runs under a Python that has faster-whisper).

Loads the model as soon as it starts (~15 s for medium on the GPU), so the caller starts it before the voice is being
generated. Then reads JSON lines on stdin:
  {"wav": "...", "out": "...json", "lang": "vi"}  -> transcribes, writes [{"word", "start", "end"}], prints DONE <out>
  {"quit": true}                                  -> frees the model and exits (the process exit releases all VRAM)
Same settings as the OmniVoice Playground Whisper runner: faster-whisper, CUDA float16 (CPU int8 fallback), beam 1,
temperature 0, no conditioning on previous text, VAD filter (500 ms silences), word timestamps, a per-language prompt.
"""
import gc, json, sys, time

PROMPTS = {
    'vi': 'Xin chào, đây là video phân tích lịch sử, quân sự và câu chuyện tài liệu.',
    'en': 'Hello, this is a documentary story and narrative analysis.',
    'es': 'Hola, este es un documental y un análisis narrativo.',
    'th': 'สวัสดี นี่คือเนื้อหาภาษาไทย về lịch sử và phim tài liệu',
    'zh': '你好，这是关于历史与军事的深度纪录片分析内容。',
}


def say(msg):
    sys.stdout.write(msg + '\n'); sys.stdout.flush()


def main():
    sys.stdout.reconfigure(encoding='utf-8'); sys.stdin.reconfigure(encoding='utf-8')
    model_path = sys.argv[1] if len(sys.argv) > 1 else 'medium'
    import faster_whisper
    t0 = time.time()
    try:
        model = faster_whisper.WhisperModel(model_path, device='cuda', compute_type='float16'); device = 'cuda'
    except Exception as e:  # noqa: BLE001 - no CUDA: CPU int8, slower but correct
        say(f'INFO cuda unavailable ({e}); cpu int8')
        model = faster_whisper.WhisperModel(model_path, device='cpu', compute_type='int8'); device = 'cpu'
    say(f'READY {device} {time.time() - t0:.1f}s')
    for line in sys.stdin:
        if not line.strip():
            continue
        job = json.loads(line)
        if job.get('quit'):
            break
        try:
            kw = dict(beam_size=1, best_of=1, temperature=0.0, condition_on_previous_text=False, vad_filter=True,
                      vad_parameters=dict(min_silence_duration_ms=500), word_timestamps=True)
            lang = job.get('lang')
            if lang and lang != 'auto':
                kw['language'] = lang
                if lang in PROMPTS:
                    kw['initial_prompt'] = PROMPTS[lang]
            t = time.time()
            segs, info = model.transcribe(job['wav'], **kw)
            words = [{'word': w.word.strip(), 'start': round(w.start, 3), 'end': round(w.end, 3)}
                     for s in segs for w in (s.words or []) if w.word and w.word.strip()]
            with open(job['out'], 'w', encoding='utf-8') as f:
                json.dump({'lang': getattr(info, 'language', ''), 'words': words}, f, ensure_ascii=False)
            say(f'DONE {job["out"]} {len(words)} words {time.time() - t:.1f}s')
        except Exception as e:  # noqa: BLE001 - reported to the caller, the worker keeps going
            say(f'ERR {job.get("out")} {e}')
    del model
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001 - torch is optional here
        pass
    say('VRAM_FREED')


if __name__ == '__main__':
    main()
