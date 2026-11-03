#!/usr/bin/env python3
"""Pick the agent's look for the next video so outfit, framing and background rotate.

Usage:
  pick_look.py [--topic "words about the video"] [--recent 6]      # prints the chosen look and why
  pick_look.py --env [--topic ...]                                  # prints LOOK_ID=..., LOOK_CODE=..., BANNER_Y=... for eval
  pick_look.py --log POSTDIR LOOK_CODE                              # record the look a finished video used
  pick_look.py --list                                               # all looks with use counts

Rules (selfie/vlog looks, PLAYBOOK "Looks"):
  1. Only SELFIE / PROPPED-PHONE looks (catalog style "selfie" or "propped") are picked. The old posed portrait looks
     (style "portrait", mouth closed) are a fallback only with --allow-portrait or when no selfie look is left.
  2. Never one of the looks used in the last 6 videos; the background must differ from the last video.
  3. Prefer the look whose background and good_for words fit the topic; then the phone hand swapped from the last video
     (phone_side left/right/none); then the least used; then the oldest last use.
  4. TOPIC_MATCH=0 means no selfie look fits the topic: the run MAY make ONE new topic look with
     scripts/make_topic_look.sh (mouth slightly open, one hand on the phone, the other free), then use it.
Looks with status other than "active" (retired, or the full-body L00c with its small face) are never auto-picked.
Data: looks/catalog.json (one entry per look) and looks/look_log.csv (one row per video).
"""
import argparse, csv, json, os, re, sys, datetime
from kit_paths import LOOKS as D
CAT, LOG = os.path.join(D, 'catalog.json'), os.path.join(D, 'look_log.csv')

def load():
    cat = json.load(open(CAT))
    rows = list(csv.DictReader(open(LOG))) if os.path.exists(LOG) else []
    return cat, rows

def shot(f):
    f = f.lower()
    size = 'medium close-up' if 'medium close-up' in f else 'close-up' if 'close-up' in f else 'full' if 'full' in f else 'medium'
    pose = 'seated' if ('seated' in f or 'sofa' in f) else 'standing'
    return size, pose

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='')
    ap.add_argument('--recent', type=int, default=6)
    ap.add_argument('--env', action='store_true')
    ap.add_argument('--log', nargs=2, metavar=('POSTDIR', 'LOOK_CODE'))
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--allow-portrait', action='store_true')
    a = ap.parse_args()
    cat, rows = load()
    by = {c['code']: c for c in cat}
    if a.log:
        post, code = a.log
        c = by[code]
        new = not os.path.exists(LOG)
        with open(LOG, 'a', newline='') as fh:
            w = csv.writer(fh)
            if new: w.writerow(['date', 'slug', 'look_code', 'look_id', 'outfit', 'framing', 'background'])
            w.writerow([datetime.date.today().isoformat(), os.path.basename(post.rstrip('/')), code, c['look_id'], c['outfit'], c['framing'], c['background']])
        print(f'logged {code} for {os.path.basename(post.rstrip("/"))}')
        return
    uses = {}
    for i, r in enumerate(rows):
        uses.setdefault(r['look_code'], []).append(i)
    if a.list:
        for c in cat:
            print(f"{c['code']:5s} {c.get('status','active'):8s} {c.get('style','portrait'):8s} used {len(uses.get(c['code'],[])):2d}x  {c['outfit']} | {c['framing']} | {c['background']}  [{c['look_id']}]")
        return
    recent = [r['look_code'] for r in rows[-a.recent:]]
    last = by.get(rows[-1]['look_code']) if rows else None
    stop = {'and', 'the', 'a', 'of', 'to', 'in', 'on', 'for', 'is', 'it', 'my', 'me', 'i', 'with', 'at', 'from', 'this', 'that', 'about', 'new'}
    stem = lambda w: w[:-1] if len(w) > 3 and w.endswith('s') and not w.endswith('ss') else w
    words = {stem(w) for w in re.findall(r'[a-z]+', a.topic.lower())} - stop
    def score(c):
        bag = {stem(w) for w in re.findall(r'[a-z]+', (c.get('good_for', '') + ' ' + c['background']).lower())}
        return len(words & bag)
    def usable(c, styles):
        if c.get('status', 'active') != 'active' or c['code'] == 'L00c' or c['code'] in recent:
            return False
        if c.get('style', 'portrait') not in styles:
            return False
        if last and c['background'] == last['background']:
            return False
        if last and c.get('style', 'portrait') == 'portrait' and last.get('style', 'portrait') == 'portrait' and shot(c['framing']) == shot(last['framing']):
            return False
        return True
    styles = ('selfie', 'propped', 'portrait') if a.allow_portrait else ('selfie', 'propped')
    pool = [c for c in cat if usable(c, styles)]
    if not pool:
        pool = [c for c in cat if usable(c, ('selfie', 'propped', 'portrait'))]
    last_side = last.get('phone_side', 'none') if last else None
    cands = []
    for c in pool:
        u = uses.get(c['code'], [])
        same_side = 1 if (last_side and c.get('phone_side', 'none') == last_side and last_side != 'none') else 0
        portrait = 1 if c.get('style', 'portrait') == 'portrait' else 0
        cands.append((-score(c), portrait, same_side, len(u), u[-1] if u else -1, c['code']))
    if not cands:  # everything excluded: fall back to least recently used active look that differs from the last one
        cands = [(0, 0, 0, len(uses.get(c['code'], [])), (uses.get(c['code']) or [-1])[-1], c['code']) for c in cat
                 if c.get('status', 'active') == 'active' and c['code'] != 'L00c' and (not last or c['code'] != last['code'])]
    cands.sort()
    pick = by[cands[0][-1]]
    if a.env:
        print(f"LOOK_CODE={pick['code']}\nLOOK_ID={pick['look_id']}\nBANNER_Y={pick.get('banner_y', 150)}\nLOOK_STYLE={pick.get('style', 'portrait')}\nPHONE_SIDE={pick.get('phone_side', 'none')}\nTOPIC_MATCH={-cands[0][0]}")
    else:
        print(f"{pick['code']}  {pick['look_id']}\n  outfit: {pick['outfit']}\n  framing: {pick['framing']}\n  background: {pick['background']}\n  good for: {pick.get('good_for','')}\n  banner_y: {pick.get('banner_y',150)}\n  style: {pick.get('style','portrait')}, phone: {pick.get('phone_side','none')}, topic match: {-cands[0][0]}{'  (no selfie look fits: you may make ONE topic look with make_topic_look.sh)' if -cands[0][0] == 0 else ''}\n  skipped (last {a.recent}): {', '.join(recent) or 'none'}")

if __name__ == '__main__':
    main()
