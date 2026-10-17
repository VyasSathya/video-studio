"""Text model for the steps that need judgment (picking clips, callouts, post drafts). Free and local first.

Picked by STUDIO_LLM (or the first that works, in this order when unset):
  claude      `claude -p` (Claude Code's own sign-in, no extra cost on a subscription)
  anthropic   ANTHROPIC_API_KEY, model STUDIO_ANTHROPIC_MODEL (default claude-sonnet-5-5); paid per token
  ollama      local Ollama at OLLAMA_HOST (default http://127.0.0.1:11434), model STUDIO_OLLAMA_MODEL
              (default mistral-nemo)
An agent driving the pipeline can skip this entirely and write the picks file itself (see repurpose.py).
"""
import json
import os
import re
import shutil
import subprocess
import urllib.request

OLLAMA = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
_chosen = None


def _claude(prompt, system):
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not found")
    full = (system + "\n\n" if system else "") + prompt
    p = subprocess.run([exe, "-p", "--setting-sources", "project,local", "--strict-mcp-config"], input=full,
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
    if p.returncode != 0 or "Failed to authenticate" in p.stdout + p.stderr:
        raise RuntimeError("claude -p failed: " + (p.stdout + p.stderr).strip()[:200])
    return p.stdout.strip()


def _anthropic(prompt, system):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    body = {"model": os.getenv("STUDIO_ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        res = json.loads(r.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in res.get("content", []))


def _ollama(prompt, system, fmt_json=False):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": os.getenv("STUDIO_OLLAMA_MODEL", "mistral-nemo"), "messages": msgs, "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 32768}}
    if fmt_json:
        body["format"] = "json"
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"]


BACKENDS = {"claude": _claude, "anthropic": _anthropic, "ollama": _ollama}


def complete(prompt, system="", want_json=False):
    """Text from the first backend that answers. With want_json, the reply is parsed (first JSON value in it)."""
    global _chosen
    order = [os.getenv("STUDIO_LLM")] if os.getenv("STUDIO_LLM") else (
        [_chosen] if _chosen else ["claude", "anthropic", "ollama"])
    errors = []
    for name in order:
        try:
            if name == "ollama":
                text = _ollama(prompt, system, fmt_json=want_json)
            else:
                text = BACKENDS[name](prompt, system)
            _chosen = name
            return parse_json(text) if want_json else text
        except Exception as e:  # try the next backend
            errors.append("%s: %s" % (name, e))
    raise RuntimeError("no text model answered: " + "; ".join(errors))


def backend():
    return _chosen


def parse_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    for opener in "{[":
        i = text.find(opener)
        if i >= 0:
            try:
                return json.JSONDecoder().raw_decode(text[i:])[0]
            except ValueError:
                continue
    raise ValueError("no JSON in model reply: " + text[:200])
