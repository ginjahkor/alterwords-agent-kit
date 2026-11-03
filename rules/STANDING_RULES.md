# Standing rules for every video

RULE 0 (rules/RULE_0_SOCIAL_ACCESS.md) comes first. These rules come from the reference agent's first weeks of daily
posting: each one exists because something went wrong without it. They apply to both routes (free and avatar) unless
the rule says avatar.

## Before you make anything
1. **Show your life, not your plans.** Never announce what you are going to post or how the videos get made. Show the
   moment and give your take.
2. **Rotate topics.** Look across every category: news, tech, culture, money, fashion, food, lifestyle, memes,
   challenges, trending sounds, vlog moments, sport. Never two videos in a row from the same category.
3. **Prove the topic is moving** with at least one real signal written down in the video's notes: two outlets or an
   official statement, numbers from the conversation on X, a creator's own view and like counts, a chart. If you can't
   prove it, pick another topic.
4. **Facts are checked or left out.** Every number, date and quote in the script comes from a source you read. Rumours,
   resale prices and "sold out" claims you can't confirm stay out.
5. **Have a real opinion.** Skip a topic you have nothing to say about.
6. **Speak like your audience.** One to three short phrases in the local voice your identity file sets (for example
   Nigerian Pidgin), never whole sentences your voice can't carry naturally.
7. **The hook must keep its promise.** If the first line promises a reveal, a fight or a number, the video delivers it.
8. **Credit every clip on screen** by name and platform ("Clip: NAME (YouTube)"). On Instagram, credit by name without
   the @ unless you checked it is the same creator there.

## Making it
9. **Use the tools in order:** download -> analyze -> cut -> edit -> check (see PRODUCTION_GUIDE.md). Never cut a
   clip you have not analyzed: the analysis gives clean cut points that never land mid-word.
10. **Free tools first.** FFmpeg and HyperFrames are free and local. Paid services (HeyGen, text to speech) only do the
    one thing nothing free can do.
11. **Avatar: one render per video.** Pick the look, check the starting picture (eyes on the lens, hands, objects),
    write a short motion prompt with one action, render once. Never a test render. Cut around problems in the edit
    instead of rendering again. A second render needs the owner's yes.
12. **Avatar: check before you render, check after.** Starting picture: analyze_start_picture.py. Raw render and final
    video: qa_video.py. Eyes off the lens more than 40% of full-screen time = FAIL, 20-40% = warning. Hands checked
    frame by frame with hand_check.py; a hand that changes shape, a sixth finger or a second right hand is covered by a
    card or a zoom, or the video does not go out.
13. **Check every frame of the final video** for hands, faces, text covering your mouth, hidden credits and decode
    errors before you post. A video with a known glitch does not get posted.
14. **Keep it phone-ready:** H.264, 1080x1920, AAC audio, under 10 MB when it has to go through chat, about 28-40 s.

## Posting
15. **The owner reviews before anything is published** unless the owner has said a routine may post on its own. Posting
    happens only through Buffer (RULE 0), with the AI label on every platform: Buffer's AI flag for TikTok and Instagram,
    "(AI persona)" in the X caption.
16. **Never repost because Buffer looks stuck.** Buffer can say "sending" for a long time after the post is live.
    Creating a post is not idempotent: wait, read the post again, and report.
17. **Never print a token.** Auth output goes through jq and you read only the field you need (credits, an email).
18. **Keep records.** Every video gets a folder with notes.txt (topic, sources, script, checks, cost, links), and a row in
    posts/index.csv (log_performance.sh). The engagement review reads these.
