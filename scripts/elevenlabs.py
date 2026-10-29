"""ElevenLabs TTS (with character timestamps) and Speech-to-Text. Every call costs credits: callers dry-run first.

The key comes from common.elevenlabs_key(); it is sent only in the xi-api-key header, never logged or written.
"""
import base64, json, mimetypes, uuid, urllib.error, urllib.request
from pathlib import Path

from common import elevenlabs_key

API = 'https://api.elevenlabs.io/v1'
# credits per character; flash/turbo are half price. Verify on elevenlabs.io/pricing before large jobs.
RATE = {'eleven_multilingual_v2': 1.0, 'eleven_v3': 1.0, 'eleven_turbo_v2_5': 0.5, 'eleven_flash_v2_5': 0.5}
NO_CONTEXT_MODELS = {'eleven_v3'}  # v3 does not take previous_text/next_text

# Delivery per emotion. Lower stability = more expressive; style exaggerates the voice's own manner.
SETTINGS = {
    'neutral':    {'stability': 0.50, 'similarity_boost': 0.75, 'style': 0.15, 'speed': 1.00},
    'calm':       {'stability': 0.60, 'similarity_boost': 0.75, 'style': 0.10, 'speed': 0.96},
    'hook':       {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.40, 'speed': 0.98},
    'tense':      {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.35, 'speed': 1.04},
    'urgent':     {'stability': 0.35, 'similarity_boost': 0.75, 'style': 0.45, 'speed': 1.08},
    'dramatic':   {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.40, 'speed': 0.94},
    'somber':     {'stability': 0.55, 'similarity_boost': 0.75, 'style': 0.30, 'speed': 0.90},
    'reflective': {'stability': 0.55, 'similarity_boost': 0.75, 'style': 0.25, 'speed': 0.93},
    'triumphant': {'stability': 0.40, 'similarity_boost': 0.75, 'style': 0.45, 'speed': 1.00},
    'question':   {'stability': 0.45, 'similarity_boost': 0.75, 'style': 0.30, 'speed': 0.97},
}
# eleven_v3 understands bracketed audio tags; used only when voice.audio_tags is true in job.json. Test first.
V3_TAGS = {'somber': '[sad]', 'reflective': '[thoughtful]', 'tense': '[tense]', 'urgent': '[urgent]',
           'dramatic': '[dramatic]', 'triumphant': '[proud]', 'question': '[curious]'}


class ApiError(RuntimeError):
    pass


def _post(url, body, headers):
    key = elevenlabs_key()
    if not key:
        raise ApiError('ELEVENLABS_API_KEY is not set (process or Windows user environment)')
    req = urllib.request.Request(url, data=body, method='POST', headers={'xi-api-key': key, **headers})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise ApiError(f'HTTP {e.code}: {e.read()[:400].decode("utf-8", "replace")}') from None


def subscription():
    """Free call: plan tier and remaining characters/credits this period."""
    key = elevenlabs_key()
    if not key:
        return None
    req = urllib.request.Request(f'{API}/user/subscription', headers={'xi-api-key': key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except (urllib.error.URLError, OSError) as e:
        return {'error': str(e)[:200]}
    return {'tier': d.get('tier'), 'used': d.get('character_count'), 'limit': d.get('character_limit')}


def credits(text, model):
    return round(len(text) * RATE.get(model, 1.0))


def tts_text(sentence, voice):
    text = sentence['text']
    if voice.get('audio_tags') and voice['model'] == 'eleven_v3' and sentence['emotion'] in V3_TAGS:
        text = f"{V3_TAGS[sentence['emotion']]} {text}"
    return text


def tts(sentence, prev_text, next_text, voice):
    """Return (mp3 bytes, alignment dict). alignment: characters + start/end seconds per character."""
    settings = {**SETTINGS[sentence['emotion']], **voice.get('settings', {}).get(sentence['emotion'], {})}
    body = {'text': tts_text(sentence, voice), 'model_id': voice['model'], 'voice_settings': settings}
    if voice.get('language_code'):
        body['language_code'] = voice['language_code']
    if voice['model'] not in NO_CONTEXT_MODELS:  # prosody continuity across separately generated sentences
        if prev_text: body['previous_text'] = prev_text
        if next_text: body['next_text'] = next_text
    url = f"{API}/text-to-speech/{voice['voice_id']}/with-timestamps?output_format={voice.get('format', 'mp3_44100_128')}"
    data = json.loads(_post(url, json.dumps(body).encode(), {'Content-Type': 'application/json'}))
    return base64.b64decode(data['audio_base64']), data.get('alignment') or data.get('normalized_alignment')


def stt(path, model='scribe_v1', language_code=None):
    """Transcribe a file with word timestamps. Costs credits per audio hour."""
    boundary = uuid.uuid4().hex
    fields = {'model_id': model, 'timestamps_granularity': 'word', 'tag_audio_events': 'false'}
    if language_code:
        fields['language_code'] = language_code
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    p = Path(path)
    ctype = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{p.name}"\r\n'
                 f'Content-Type: {ctype}\r\n\r\n'.encode() + p.read_bytes() + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    raw = _post(f'{API}/speech-to-text', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    return json.loads(raw)
