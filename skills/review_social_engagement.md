# Skill: Review my social engagement

A daily self-review of your own posts and engagement, at a time that does not clash with your posting times, reported
to your owner as a short text.

## Top priority
Use only the Buffer API for all social-account access: posts, status and engagement. Never open social websites, use
browser logins, scrape public social pages, or fall back to direct platform access (rules/RULE_0_SOCIAL_ACCESS.md).
Keep credentials private. If data cannot be retrieved through Buffer, report that limitation with no fallback.

## Runtime
1. Read your Buffer workflow (skills/post_to_socials_with_buffer.md) and your engagement records
   ($AGENT_POSTS/index.csv, your playbook's experiments log, earlier reviews).
2. Through Buffer, retrieve recent posts and metrics on TikTok, Instagram and X, prioritising posts since the last
   review, and compare the last seven days with the seven before when available
   (`buffer posts get --id ID --fields metrics.type,metrics.value,metricsUpdatedAt`, or scripts/log_performance.sh).
3. Buffer gives comment COUNTS, not comment text. Never claim "no comments" when retrieval failed or is unsupported.
   Keep unavailable metrics separate from real zeros. Capture views/impressions, likes, comments, shares, saves,
   follower changes and watch time where available, and say which fields are unavailable. Do not infer account
   penalties or posting failures from what Buffer can't show.
4. Analyse hooks, topics, opening visuals, length, posting time, music, questions and follow lines using actual samples.
   Separate observation from hypothesis; no causal claims from small samples. Name what is working, what is
   underperforming, and one or two testable improvements, each with a metric and a review window. Don't keep changing
   things before an experiment has enough data.
5. Save a dated review record in your working folder (evidence, limitations, recommended experiments, outcomes of
   earlier experiments). Future content runs may use these recommendations within what your owner already approved.
6. Do not change other skills, schedules, account settings or posting cadence, and do not post, delete, reply or follow
   as part of this routine. Flag changes that need your owner's approval. Never manufacture engagement.

## Report
Key findings with the real numbers, what to improve, and what Buffer could not show. Short.
