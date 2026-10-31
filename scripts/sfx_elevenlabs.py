"""Add documentary/motion-graphics sound effects to assets/sfx/<type>/ with the ElevenLabs Sound Effects API.
The chibi workflow's library (history-video-workflow/assets/sfx) is reused for battlefield sounds; this adds what
title cards, typed text and maps need. Existing files are never regenerated.

  PY scripts/sfx_elevenlabs.py            dry run (plan + live balance)
  PY scripts/sfx_elevenlabs.py --run      generate missing files, log measured credits in assets/sfx/LICENSES.md
"""
import argparse, datetime, json, sys, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, elevenlabs_key
from elevenlabs import subscription

OUT = ROOT / 'assets' / 'sfx'
LIB = {  # type -> [(seconds, prompt)]
    'typewriter': [(4.0, 'Vintage mechanical typewriter typing fast, crisp key strikes, close, dry, no music'),
                   (2.0, 'Old typewriter typing a few slow deliberate keys, close, dry, no music'),
                   (10.0, 'Vintage manual typewriter typing continuously at a steady even pace, loud crisp mechanical key strikes, '
                          'close mic, dry, no bell, no carriage return, no music')],
    # card hits (the first set was too thin under narration; first used by nguoi-gac-dem)
    'titlehit': [(5.0, 'Massive cinematic movie trailer title hit, huge sub bass boom, metallic slam and deep dark braam, '
                       'long reverb tail, thriller, no melody'),
                 (4.0, 'Epic dark cinematic impact, heavy orchestral drum slam with distorted sub drop and long tail, no melody')],
    'chapterhit': [(3.0, 'Deep dark cinematic documentary transition hit, low boom with short metallic ring and reverb tail, no melody'),
                   (3.0, 'Heavy low taiko slam with sub boom, cinematic chapter card, dark, no melody')],
    'subdrop': [(3.0, 'Deep cinematic sub bass drop, low rumble falling in pitch, no melody')],
    'revswell': [(3.0, 'Reverse cymbal and reverse piano swell rising into a hit, dark cinematic suck-in, no melody')],
    'whooshdark': [(1.5, 'Fast deep cinematic whoosh pass-by, dark, airy, no music')],
    'typebell': [(1.5, 'Typewriter carriage return lever with end-of-line bell ding, close, dry')],
    'impact': [(3.0, 'Deep cinematic trailer impact hit with sub boom and long dark reverb tail, no music'),
               (2.5, 'Heavy cinematic braam hit, low brass and distorted sub, documentary title, no melody')],
    'riser': [(3.0, 'Dark cinematic riser building tension into a hit, reverse swell, no melody')],
    'reveal': [(1.2, 'Short low whoosh with soft metallic shimmer for a text reveal, cinematic, no music')],
    'mapping': [(1.5, 'Subtle digital UI sweep and soft beep for a map marker appearing, military briefing, no music')],
    # espionage / night-story foley (first used by nguoi-gac-dem)
    'knock': [(2.5, 'Three slow firm knocks on an old wooden door at night, close, dry, no music')],
    'jeep': [(5.0, 'Old 1960s military jeep approaching slowly on a dirt road at night and stopping with a soft brake squeal, engine idle, no music')],
    'brakes': [(3.5, 'Several old military trucks braking hard and stopping on a dirt road, doors slamming, no music')],
    'motorbike': [(3.0, 'Old motorbike pulling up fast and braking on gravel, engine cut, no music')],
    'clang': [(1.5, 'Iron rod pushed through liquid striking the metal bottom of an oil drum, single dull clang, close, no music')],
    'knockfloor': [(1.5, 'Bayonet tip tapping a hard wooden floor plank, one dull hollow knock, close, dry, no music')],
    'glass': [(1.5, 'Small glass bottle dropped and shattering on a hard floor, close, no music')],
    'rooster': [(4.0, 'Distant rooster crowing at dawn over a quiet rural village, soft, no music')],
    'match': [(3.0, 'Match struck, a small slip of paper catches fire and burns briefly, close, quiet, no music')],
    'night': [(10.0, 'Quiet tropical night ambience, crickets and distant insects, faint far-off dog bark, no music')],
    'lock': [(2.0, 'Old padlock mechanism clicking open as a key turns, metallic, close, dry, no music')],
    'heartbeat': [(4.0, 'Slow deep heartbeat thumps, low and muffled, cinematic tension, no music')],
    'clock': [(6.0, 'Old wall clock ticking slowly in a silent room, close, no music')],
    # submarine / naval (first used by the Akula film)
    'sonarping': [(4.0, 'Single active sonar ping underwater, clean metallic ping with long echoing reverb tail, deep ocean, no music'),
                  (5.0, 'Distant submarine sonar ping heard through water, soft and eerie with a faint returning echo, no music')],
    'hullcreak': [(4.0, 'Submarine steel hull groaning and creaking under deep water pressure, low metallic stress sounds, no music')],
    'torpedolaunch': [(3.0, 'Submarine torpedo tube firing underwater, sharp high-pressure air whoosh and thud, then propeller whine racing away, no music')],
    'underwater': [(10.0, 'Deep underwater ocean ambience inside a quiet submarine, low muffled rumble, faint distant whale-like groans, no music')],
    'propwash': [(5.0, 'Large submarine propeller passing close overhead underwater, rhythmic deep churning wash, muffled, no music')],
    # weapons footage (cold open and SINKEX shots; user review 2026-10-31: "too gentle for a military film")
    'navalblast': [(4.0, 'Massive close torpedo warhead detonation under a warship, huge deep boom, roaring water column erupting and '
                         'crashing back down, metal groan, no music'),
                   (4.0, 'Huge close explosion on a warship hull, sharp violent blast, fireball roar, debris and metal shrapnel '
                         'raining down, no music')],
    'missilelaunch': [(4.0, 'Naval missile launch from a vertical launch cell, violent ignition blast then deafening rocket roar '
                            'climbing away, no music')],
    # audible layer over the sub-bass card hits (impact/titlehit are ~100 % below 150 Hz: inaudible on laptop speakers)
    'cardslam': [(1.5, 'Punchy cinematic trailer slam hit, sharp metallic transient with a mid-range body and short bright tail, '
                       'close, no music')],
    # subscribe call-to-action overlay (scenes/kit/subscribe.js; user review 2026-10-31)
    'mouseclick': [(0.5, 'Single crisp computer mouse button click, close, dry, no music')],
    'subscribed': [(1.5, 'Bright satisfying UI confirmation pop with a short sparkling chime, clean, modern, no music')],
    'notifybell': [(1.5, 'Small bright notification bell ringing twice quickly, clean UI sound, no music')],
    # pre-modern warfare: black-powder guns, river fleets, war elephants (first used by 5-nguyen-huu-canh)
    'cannon': [(4.0, 'Single old bronze muzzle-loading cannon firing, deep black powder boom, rolling echo over water, no music'),
               (4.0, 'Several old black powder cannons firing in a ragged salvo from boats on a river, booming echoes, no music')],
    'musket': [(3.0, 'Massed matchlock musket volley, many black powder guns firing together, crackling roar and echo, no music')],
    'elephant': [(3.0, 'War elephant trumpeting loudly in panic, close, raw, no music')],
    'gong': [(4.0, 'Large bronze war gong struck hard twice, deep shimmering ring, Southeast Asian, no music')],
    'mosquito': [(4.0, 'A single mosquito buzzing close to the ear, high whine passing left to right, quiet night, no music')],
    'oars': [(6.0, 'Many wooden oars rowing in unison on a river, rhythmic splashes and creaking wooden boat, no music')],
    'river': [(10.0, 'Wide tropical river ambience at dawn, gentle water lapping against a wooden boat hull, distant birds, no music')],
    # 1870-71 warfare (first used by the Reichsverfassung film)
    'artillery': [(4.0, '19th century steel breech-loading field gun battery firing, sharp heavy black powder cracks one after another, '
                        'rolling thunder over open fields, no music'),
                  (4.0, 'Single heavy siege gun firing in winter, huge deep boom with long echo over a city, no music')],
    'shellburst': [(3.0, 'Artillery shell whistling in and exploding on impact in a field, earth and stones raining down, no music')],
    'rifles': [(3.0, 'Infantry line firing a ragged volley of 19th century breech-loading rifles, crackling black powder shots, no music')],
    'gallop': [(5.0, 'Heavy cavalry charge, hundreds of horses galloping closer on hard ground, thundering hooves, '
                     'jingling tack, distant shouts, no music')],
    'sabre': [(1.5, 'Cavalry sabres drawn from steel scabbards together, sharp metallic ring, no music')],
    'march': [(6.0, 'Column of infantry marching in step on a cobbled road, heavy boots, rattling equipment, no music')],
    'steamtrain': [(6.0, 'Old 19th century steam locomotive pulling away, chuffing and hissing steam, whistle, iron wheels on rails, no music')],
    'telegraph': [(3.0, 'Old 19th century telegraph key tapping morse code, sharp clicking sounder, close, dry, no music')],
    'bugle': [(3.0, 'Distant military bugle signal call on a battlefield, single brass horn, slightly echoing, no music')],
    # el_01 came out as quiet bolt clicks, not a shot (user review 2026-11-01): use el_02/el_03
    'gunshot': [(1.5, 'Single shot of a 19th century breech-loading black powder rifle, sharp crack with short echo outdoors, no music'),
                (2.0, 'One single loud rifle gunshot, powerful black powder blast with deep boom and rolling echo over an open '
                      'battlefield, no mechanical clicks, no reloading sounds, no music'),
                (2.0, 'A single very loud musket shot fired outdoors, explosive bang with smoke whoosh and long echo, '
                      'no clicks, no bolt sounds, no music')],
    'mgburst': [(3.0, 'Hand-cranked 19th century multi-barrel volley gun firing a rapid rattling burst, black powder, outdoors, no music')],
    'hurrah': [(4.0, 'Large hall full of uniformed officers cheering hurrah three times, sabres rattling, echo in a palace hall, no music')],
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', action='store_true'); a = ap.parse_args()
    todo = [(t, i, s, p) for t, items in LIB.items() for i, (s, p) in enumerate(items, 1)
            if not (OUT / t / f'el_{i:02d}.mp3').exists()]
    sub = subscription(); left = sub['limit'] - sub['used'] if sub and sub.get('limit') else None
    print(f'{len(todo)} to generate, {sum(s for _, _, s, _ in todo):.1f} s (~{sum(s for _, _, s, _ in todo) * 10:.0f} credits '
          f'at the measured ~10 credits/s); balance {left}')
    if not a.run:
        return
    lic = OUT / 'LICENSES.md'
    for t, i, s, p in todo:
        before = subscription()
        req = urllib.request.Request('https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128', method='POST',
                                     data=json.dumps({'text': p, 'duration_seconds': s, 'prompt_influence': 0.5}).encode(),
                                     headers={'xi-api-key': elevenlabs_key(), 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            sys.exit(f'{t}: HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}')
        f = OUT / t / f'el_{i:02d}.mp3'; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
        after = subscription(); cost = after['used'] - before['used'] if after and before and 'used' in after and 'used' in before else None
        with open(lic, 'a', encoding='utf-8') as fh:
            fh.write(f'- `{t}/{f.name}` — ElevenLabs Sound Effects, {datetime.date.today()}, Starter plan commercial licence '
                     f'(confirmed 2026-10-30). {s} s, {cost} credits. Prompt: "{p}"\n')
        print(f'{t}/{f.name} ok ({cost} credits)')


if __name__ == '__main__':
    main()
