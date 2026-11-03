# Templates

- `hyperframes/clip_card/`: a 16:9 source in a rounded 1000x563 card at y=430 over a blurred copy, pill + title at
  y=190, progress bar at y=1010, captions from y=1090, credit line at y=1280.
- `hyperframes/title_card/`: pill and a two-line title, for the hook card from frame 0 and the end card.
- `hyperframes/word_captions/`: captions that pop in word by word and turn the accent colour while each word is said.
- `hyperframes/talking_head_captions/`: a vertical talking head full screen with captions from y=1120 (avatar route).
- `heygen_request_template.json`: the shape of one avatar render request (avatar route). Placeholders only.

Run `bash templates/make_test_assets.sh` once to make the `assets/` videos: plain test patterns so each layout renders
as it is. `scripts/hf_build.py` builds the real
projects from these layouts with your own clips, words and colours from settings.env. Colours and fonts come from
AGENT_ACCENT, AGENT_INK, AGENT_BG, AGENT_FONT_DISPLAY and AGENT_FONT_BODY.
