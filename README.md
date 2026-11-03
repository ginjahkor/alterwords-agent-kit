# AlterWords agent production kit

Everything an AlterWords agent needs to make short vertical videos for TikTok, Instagram and X with free tools, and to
post them through the Buffer API. It holds the scripts, the rules, the HyperFrames layouts, the skills written out as
instructions, the production guide and an example settings file.

The kit contains no keys, tokens, passwords, cookies, account IDs or channel IDs. Each agent adds its own in
`settings.env`, which never goes back to the repo.

## Start

```
git clone https://github.com/ginjahkor/alterwords-agent-kit.git blueprint-kit && cd blueprint-kit
cp settings.example.env settings.env      # fill in your name, handles, colours, fonts, voice, avatar or none
bash install.sh                           # add --with-avatar only if your owner gave you an avatar
bash selftest.sh
```

Then read, in this order:
1. `rules/RULE_0_SOCIAL_ACCESS.md`: your own social accounts are touched only through the Buffer API.
2. `rules/STANDING_RULES.md` and `rules/ENGAGEMENT_RULES.md`.
3. `PRODUCTION_GUIDE.md`: how a video is made, on the free voiceover route or the avatar route.
4. `skills/make_a_video.md`: the end-to-end recipe, which calls the other skills by name.

To update later: `git pull`, then `bash selftest.sh`.

## What is where

- `scripts/`: downloading (YouTube through the free WARP route, TikTok), source analysis and transcription, avatar
  look and render tools, quality checks (hands, face, gaze, glitches), HyperFrames builds, Buffer posting and
  performance logging. `env.sh` loads your settings; every script reads paths and names from it.
- `rules/`: RULE 0, the standing rules, the engagement rules, the prompt template for avatar pictures and motion, the
  playbook and the tool overview.
- `templates/`: the HyperFrames layouts (clip card, title card, word captions, captioned talking head) and an example
  HeyGen request. `templates/make_test_assets.sh` makes plain test-pattern sample videos for them.
- `skills/`: each video skill written out as instructions: download YouTube, download TikTok, analyze and transcribe,
  HyperFrames edit, FFmpeg overlay, post with Buffer, make a video, daily posting routine, review engagement.
- `soundboard/`: the index and credits for 19 sound effects; `scripts/soundboard.sh` downloads them and mixes them in.
- `scripts/export_final.sh`: the export step (join segments, match loudness, -14 LUFS, chat copy).
- `INSTALL_PROFILES.md`: every tool with its tested version, how it is installed, how to check it.
- `PRODUCTION_GUIDE.md`: the full guide, including voiceover, your look, checks, failures and testing new tools.
- `settings.example.env`: every setting with a placeholder.

## Rules that never bend

- Buffer API only for your own TikTok, Instagram and X. No browser logins, no scraping your own pages.
- AI disclosure on every post.
- Never fake a picture of a real person or event, never invent comments or numbers, never pretend to be human.
- Never commit a key. Run a secret scan before every push.
