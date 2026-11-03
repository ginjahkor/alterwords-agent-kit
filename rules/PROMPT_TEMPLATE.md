# Picture-analysis checklist and prompt template (avatar route)

Why this exists: on the reference agent's videos the content was good but the generation was the problem: the eyes
looked the wrong way and the hand and phone were not generated properly. Every start picture has to be described in
full, and the prompt has to match it exactly.

What the measurements showed:
- The start picture already had the eyes turned to one side and the head yawed 11 degrees.
- The render then had the eyes DOWN for most of the video (normal lens gaze reads 0.40-0.47 on the down score).
- The old default motion prompt literally said "Talking to the phone at arm's length" - that points the eyes at the
  phone screen, not the lens.
- HeyGen's custom motion only covers the first 10 seconds and then loops or holds, so one bad gesture repeats.

## What the research says (sources)

Higgsfield (their own pages):
- higgsfield.ai/blog/photo-to-ai-video: a reference photo plus a detailed motion prompt beats text alone. Describe the
  specific motion, what the background does, and the pacing ("slow and deliberate" vs "fast and abrupt"). Use a sharp,
  well-lit source photo with a clear subject; cluttered or blurry photos distort. Check the still BEFORE the video,
  because a new still is cheaper than a new video. Give exact camera and motion instructions, never "make it move".
- higgsfield.ai/sora-2-prompt-guide: one camera move and one subject action per shot, with a strong specific verb.
  Detail the shot like a storyboard: framing, depth of field, lighting, action. Anchor foreground, midground and
  background so things stay where they are. Talking-head example format: "UGC reaction video, authentic, handheld,
  shot on front iPhone camera". Anything you leave out, the model invents.
- A Segmind guide to Higgsfield's prompt format (third party, segmind.com): the first frame controls everything;
  keep image (framing, light, background), identity and motion in separate prompts; short direct sentences beat long
  paragraphs; say each rule once; avoid vague words like "cinematic" or "dynamic".

HeyGen (what I actually render with):
- help.heygen.com article 12805098, "Fine-Tune Avatar Gestures and Movements with Custom Motion Prompts":
  - Controllable: facial expression, hand gestures, posture, GAZE ("look at camera"), stillness ("hands still",
    "barely move").
  - NOT controllable: camera motion, scene, PROPS OR ACTIONS ("pick up a phone"), walking, background or lighting.
  - Structure: body part + action + emotion, e.g. "Right arm raises in a wave, enthusiastic and friendly."
  - One gesture per prompt, optionally with one expression; at most a two-beat "X, then Y"; under two short clauses.
  - No timing or seconds; HeyGen paces it. Small wording changes make big differences; if it fails, simplify.
  - Custom motion is generated for 10 seconds max, then loops or holds for the rest of the scene.
  - Avatar V adds Expression, Gesture and Gaze presets and "maintains realistic eye contact". (The kit renders with Avatar IV
    through the API; check whether the API offers Avatar V before your first render.)

What that means for me: the DETAILED frame description goes into (1) the picture prompt, because the first frame decides
where my eyes, hands and phone are, and (2) my own written analysis, which I check the prompt against. The motion prompt
itself stays SHORT and exact: gaze first, the phone arm still, one free-hand gesture named by where that hand is.
Never ask HeyGen to do anything with the phone: it cannot control props, and naming one invites a warped one.

## A. Picture prompt (make the starting picture first)

One field per line, said once, no vague words:
- Shot + subject: selfie of me (the agent, my reference face from my identity file), chest-up, arm's length, 9:16.
- Eyes and head: looking directly into the camera lens, head straight to camera, chin level.
- Mouth and expression: mouth slightly open mid-word, warm natural expression.
- Phone: held in my RIGHT/LEFT hand just outside the frame (phone not visible), or propped in front of me.
- Free hand: one free hand at chest height on the [left/right] side of the frame, palm toward camera, five relaxed
  separate fingers. Exactly two hands in total. No second person close behind me.
- Outfit: [one outfit].
- Background: [one place, 2-3 concrete objects], soft background blur, stays still.
- Light: [one light source and direction], sharp face, no clutter.

## B. Picture-analysis checklist (scripts/analyze_start_picture.py IMAGE --look Lxx)

Run it on the exact picture HeyGen will animate, read every line, and write it into the post folder
(picture_analysis.json + motion_prompt.txt). render_avatar.sh now refuses to render without a passed analysis.
1. Eyes: INTO THE LENS? (down below 0.62, up below 0.55, sideways within 0.40). If not: remake or pick another look.
2. Head: facing the camera, yaw within 15 degrees, chin level?
3. Face: where in the frame (third), top of the face (for the headline), mouth slightly open (0.03-0.10)?
4. Body: square to the camera or turned with the head?
5. Each hand: which side of the picture, height (chin / chest / waist / bottom edge), palm direction, fingers, does it
   reach the frame edge (that is the phone arm). MediaPipe's left/right label is unreliable on my pictures, so prompts
   name hands by where they are in the frame; the phone hand comes from the catalog.
6. What I hold: phone visible or not, which hand, propped or held. Cups, laptops and other objects.
7. People: only me big in the frame; small background people are fine.
8. Background: from the catalog (place, objects, light). It must stay still.
9. Then the existing checks: face match, hand_check.py on the full shot AND the hand close-up (rule 4), pose_check.py.
Any problem = do not render. Fix the picture first (about 1 credit) or use another look.

## C. Motion prompt template (HeyGen Avatar IV, one line)

    Looks straight into the camera lens the whole time, [one expression]; the [right/left] arm holding the phone stays
    still, and the free hand on the [left/right] of the frame makes small slow open-palm gestures, five relaxed fingers.

Rules for it:
- Gaze clause first, every time. Never "talking to the phone", "looking at the screen" or "reading".
- One expression word that fits the topic (warm, confident, amused, serious). Serious topics get serious.
- The phone gets only a stillness clause. Never ask it to move, show, tilt or change hands.
- One free-hand gesture only, named by its place in the frame and its height from the analysis.
- If no free hand is visible: "hands still, gentle natural nods" (and prefer a look that has a checked free hand).
- Propped phone: "hands stay relaxed in the lap".
- Nothing about the camera, the background or walking (HeyGen ignores or breaks on them). My gentle handheld drift is
  added in editing.
- No seconds or timing. Under about 45 words.
- The first 10 seconds of motion loop, so the gesture must look fine repeated.

## D. After the render (rule 1 check, now with gaze)

scripts/qa_video.py now also measures where my eyes point in every sample: eyes down / up / sideways and head turned
away. Over 40% of my full-screen samples off the lens = FAIL; 20-40% = warning, look at those frames.
Calibrated on six of the reference agent's renders: the one with the eyes visibly on the phone read 43% eyes down (FAIL); the others
read 27-33% (warnings).

Keep your own gaze audit of your looks in $AGENT_LOOKS/ (which looks are into the lens, which must be remade first).
