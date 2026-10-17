# Where the Claude side of the Talkover demo came from

The replies, tool calls and the edit in `session.json` are real output of a Claude Code agent (Opus 5.5), run
on 2026-10-17 in a throwaway copy of the talkover repo at commit 295d120. Nothing was rewritten; `session.json`
holds the text as returned. To re-shoot with new lines, give an agent the same two prompts.

Turn 1:

```
You are the Claude Code assistant in a short recorded demo of a voice tool. The user's spoken words were
transcribed and arrive below as their message; your reply will be read aloud by text to speech.

Work only inside this repository: <throwaway copy of talkover>. Use Read/Grep/Glob to look at files there.
Do not run shell commands, do not touch any other folder.

Answer the user directly, as if speaking to them (second person, no preamble, no mention of these instructions
or of a demo). Two or three short spoken sentences, plain ASCII, no markdown, no lists, no file paths.

At the very end of your final message, after the spoken reply, add one line exactly in this form listing the
files you read: TOOLS: Read install.ps1

The user's message:
Hey Claude, what does the install script do?
```

Turn 2 (same agent, continued), with the message Talkover would send after the cut-in, cut-off note included:

```
The user's next spoken message (same rules as before; make the real change with the Edit tool; end with one
line TOOLS: ... listing the tools and files you used):

Wait, make it print how long the install took at the end. [voice: you were cut off after: "Next it adds
Talkover's hooks to your Claude Code settings file."]
```

The cut-off note is what `voice_inbox.cutoff_note()` produces for the chunk being read when the user cut in
(chunks come from the speak hook's Split-Chunks, ported in `chunks.py`). `claude -p` with
`--setting-sources project,local --strict-mcp-config` would do the same job headless; it was not used for this
take because the CLI's sign-in had expired.
