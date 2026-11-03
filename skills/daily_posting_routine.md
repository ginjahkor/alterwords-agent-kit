# Skill: Daily posting routine (twice a day)

The routine that runs "Make a video" on a schedule and posts the result to TikTok, Instagram and X. The reference agent
posts at 6 AM and 5 PM local time and reviews engagement at 10 AM, so the review never collides with a post. Pick your
own times with your owner and keep them fixed.

## Each run
1. Read RULE 0, STANDING_RULES, ENGAGEMENT_RULES, your identity file, your playbook and the newest engagement review.
2. Check the last post's category in $AGENT_POSTS/index.csv and pick a different one. Mix trending topics with your own
   life (vlogs, what you did today); show what you did, never announce plans.
3. Run "Make a video" end to end: trend evidence, source clip, analysis, script, voice, edit, checks, captions.
4. Send the checked video to your owner as soon as it passes, with the short text from step 11 of "Make a video".
5. Post with "Post to socials with Buffer" when your owner has approved scheduled posting for this routine (or approves
   this video). Confirm each post in Buffer only and report the three links from Buffer.
6. Log the post (index.csv, playbook experiments row, follow line yes/no, trend sound yes/no) and any lesson.

## If something fails
- No trend you can verify: post a life/vlog video instead; never invent a trend.
- A check fails and editing can't fix it: don't post; tell your owner what failed. Avatar route: at most one re-render.
- Buffer refuses or a channel is disconnected: stop, report Buffer's message, and ask your owner to reconnect it in
  Buffer.
- Never post twice for one slot; check `buffer posts list` before any retry.

## Report each run
The video, the topic and take, the three Buffer links (or what failed), checks passed, and credits used if any.
