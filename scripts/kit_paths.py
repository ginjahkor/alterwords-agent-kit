"""Paths and settings for the kit's Python scripts.

Reads KIT_HOME/settings.env (plain KEY=value lines) so Python works the same as the bash scripts,
even when env.sh was not sourced. Values already in the environment win.
Usage inside a script:  from kit_paths import HOME, WORK, LOOKS, MODELS, SCRIPTS, setting
"""
import os, re

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
KIT = os.environ.get("KIT_HOME") or os.path.dirname(SCRIPTS)

_vals = {}
_f = os.path.join(KIT, "settings.env")
if os.path.exists(_f):
    for line in open(_f, encoding="utf-8"):
        line = line.split(" #")[0].strip() if not line.lstrip().startswith("#") else ""
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if m:
            _vals[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def _expand(v):
    v = v.replace("$HOME", os.path.expanduser("~"))
    return re.sub(r"\$\{?([A-Z_][A-Z0-9_]*)\}?", lambda m: setting(m.group(1), ""), v)


def setting(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    if name in _vals and _vals[name] != "":
        return _expand(_vals[name])
    return default


HOME = setting("AGENT_HOME", os.path.expanduser("~/agent_studio"))
WORK = setting("AGENT_WORK", os.path.join(HOME, "work"))
POSTS = setting("AGENT_POSTS", os.path.join(HOME, "posts"))
LOOKS = setting("AGENT_LOOKS", os.path.join(HOME, "looks"))
MODELS = setting("AGENT_MODELS", os.path.join(HOME, "models"))
NAME = setting("AGENT_NAME", "Agent")
FONT = setting("AGENT_BANNER_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
