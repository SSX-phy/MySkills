---
name: tmux-usage
description: >
  Drive a local tmux session programmatically — create a named detached session,
  send commands into it via send-keys, and read the pane back through a
  continuously-streamed pipe-pane log, with capture-pane as a fallback. On Windows
  this is WSL tmux. Use this skill whenever the user wants to run commands inside a
  tmux session from Claude Code: SSH-in-tmux to a remote host, long-running local
  jobs, or anything where the work lives behind a tmux pane that Claude itself is
  not attached to. Also use it whenever a task names a tmux session and asks Claude
  to put commands into it or capture its output.
when_to_use: >
  Trigger phrases: "open a tmux session", "send a command to tmux", "capture the
  tmux pane", "log the tmux session", "drive the remote host through tmux", or
  whenever a task involves a tmux session name plus commands to run inside it.
  Also trigger on any request that mentions feeding a long-running interactive
  shell from outside it.
allowed-tools: Bash, Read
---

# Tmux Usage

Drive a tmux session that Claude is not attached to. The pattern is the same
whether the pane holds a local shell, a long-running job, or an SSH connection to
a remote host: you give the session a name, push commands in with `send-keys`,
and read the pane back by tailing a continuously-streamed log (`pipe-pane`) from a
remembered line cursor, with `capture-pane` as the fallback when the log isn't
available.

The skill has four parts: **Init**, **Interacting**, **Log**, and **Other tmux
knowledge**. Read them in order the first time; after that, jump straight to the
section you need.

**On Windows, this skill is WSL tmux — and the send path and the read path are
split.** There is no native Windows tmux; it lives in your WSL distro and it's the
real Linux build, so the tmux workflow is identical to Linux. But on Windows,
*talking to tmux* and *reading the log* go through different tools, and this split
is a hard rule — do **not** collapse it back into "wrap everything in WSL":

- **Send / control the session — always inside WSL.** Every command that talks to
  tmux (`new-session`, `set`, `pipe-pane`, `send-keys`, `display-message`,
  `kill-session`, `capture-pane`, …) runs from a non-interactive tool call wrapped
  as `wsl -e bash -lc "<command>"`, with WSL paths (`$WSL_SAVE_DIR` → `/mnt/d/...`).
- **Read the log — always via PowerShell `Get-Content`, never WSL.** The pipe-pane
  log is an ordinary Windows-side file (`$WIN_LOG` → `D:\...\<name>.log` — the very
  same file `pipe-pane` writes to at `/mnt/d/...`). Reading a local file never needs
  to cross into WSL, so **never read it with `wsl … tail/head/cat/wc`**; use
  PowerShell `Get-Content` (conversions below).
- **Send and read are separate tool calls.** Never bundle a read onto a send
  (no `send-keys … ; sleep … ; tail …` in one shot) — the send is WSL, the read is
  PowerShell, so they cannot share a command line anyway. Send, wait, then read in a
  second call.
- **`capture-pane` is not a read path on Windows.** It is a WSL/tmux command, so it
  can never satisfy the PowerShell-read rule. Use it only as a control command to
  rebuild a lost log (§3), never as the routine way to read output.

PowerShell conversions for every read this skill uses (`$WIN_LOG` is the log):

| Purpose | Linux / in-WSL form — NOT for reading on Windows | Windows read (use this) |
| --- | --- | --- |
| Line count (cursor) | `wc -l < $WSL_SAVE_DIR/<name>.log` | `@(Get-Content $WIN_LOG).Count` |
| Reply since cursor | `tail -n +$(($LOG_CURSOR+1)) …` | `Get-Content $WIN_LOG \| Select-Object -Skip $LOG_CURSOR` |
| Last N lines (peek) | `… \| tail -10` | `Get-Content $WIN_LOG -Tail 10` |

To read the reply *and* refresh the count in one PowerShell call:
`$l = Get-Content $WIN_LOG; $l | Select-Object -Skip $LOG_CURSOR; '---'; $l.Count`.

The one interactive exception is `tmux attach`, which needs a real terminal: open a
`wsl` shell yourself and attach there, not through a tool call (a non-interactive
call fails with `open terminal failed: not a terminal`). Sessions live in the WSL
instance, so keep at least one WSL shell alive or WSL2 may shut down and drop them.

---

## 1. Init

Name the session and create it detached so it survives independently of the
shell that ran the command:

```
tmux new-session -d -s <name>
```

The name is the **handle** every subsequent tmux command will use via `-t <name>`.
**Name it `<server>_<task>`** — e.g. `Dirac_MnO` for an MnO job on the host
`Dirac` — so the handle states both where it runs and what it does, and stays
unique across concurrent sessions. For a purely local job with no remote host,
use the role of the machine or `local` in the server slot. If a session with that
name already exists, this command will error rather than clobbering it; that's
usually what you want, but check with `tmux ls` first if you're unsure.

**Subagent-opened sessions get a `_Sub_` tag.** When a **subagent** (not the main agent)
creates the session, name it `<server>_<task>_Sub_<subagent_task>` — inherit the parent
session's `<server>_<task>` head (so it traces back to the run) and append
`_Sub_<subagent_task>` to label it as subagent-opened (e.g. parent `Bohr_Ce` → subagent
analysis session `Bohr_Ce_Sub_aly100`). Open a distinct session — never reuse or `send-keys`
into the parent's pane. (Such sessions are closed when the subagent ends — see §5.)

**Arm logging here, not later.** The streamed log is your primary way of reading
the pane (Section 2), so turn it on immediately — before anything runs in the
session — so the very first output is captured. Clear any stale log, raise the
scrollback depth that backs the `capture-pane` fallback, then start `pipe-pane`:

```
[ -s $WSL_SAVE_DIR/<name>.log ] && mv $WSL_SAVE_DIR/<name>.log $WSL_SAVE_DIR/<name>.log.prev
tmux set -t <name> history-limit 50000          # depth for the capture-pane backup
tmux pipe-pane -t <name> -o "cat >> $WSL_SAVE_DIR/<name>.log"
```

On Windows run each of these arming commands (they talk to tmux) via
`wsl -e bash -lc '<cmd>'`, with `$WSL_SAVE_DIR` a WSL path (e.g. `/mnt/d/.../<name>.log`);
the same file is read back through PowerShell as `$WIN_LOG` (e.g. `D:\...\<name>.log`)
— never re-read it through WSL (see the send/read split in the intro). Then
initialize the **log cursor** — an inline context variable Claude holds, like
`$SCOPE_ROOT` — to `$LOG_CURSOR = 0`. Section 2 advances it after every command.

Whatever the pane is supposed to *run* (SSH into a remote host, activate a conda
environment, start an interactive REPL), do it as the first step in the
Interacting section below — not here. Init creates the session and arms logging;
nothing more.

Before creating a session, use the 'tmux ls' command to check the existing sessions and prevent naming conflicts.

**Reusing a session you didn't create (attach, don't open).** If `tmux ls` shows
the session you want already exists, don't `new-session` over it — adopt it. First
**check whether it's already being piped** before arming anything, because it may
already have a log you should reuse:

```
tmux display-message -p -t <name> '#{pane_pipe}'    # 1 = piping active, 0 = not
```

- **Already piping (`1`) — adopt the existing log, don't re-arm.** tmux has no
  format variable for the pipe *destination*, only `#{pane_pipe}` for on/off; find
  the path from the process table, since `pipe-pane` forks `sh -c "<command>"`:
  `ps -ef | grep 'cat >>'` → e.g. `sh -c cat >> /path/<name>.log`. Use that file as
  your read channel and set `$LOG_CURSOR` to its **current line count** — on Windows
  `@(Get-Content $WIN_LOG).Count` via PowerShell, on Linux `wc -l` — not 0, since the
  log already holds history. Do **not** re-run `pipe-pane`: that replaces the existing
  pipe and breaks continuity with whatever set it up.
- **Not piping (`0`) — arm logging yourself**, exactly as in the Init block above:
  raise `history-limit`, start `pipe-pane`, and reset `$LOG_CURSOR = 0`.

Either way, do **not** settle for reading the pane with `capture-pane` as your read
path; it's a bounded backup, not the channel (and some environments forbid it
outright — check the user's CLAUDE.md). Two cautions when adopting a session:

- **It may be attached / live.** `tmux ls` marks an attached session `(attached)` —
  someone (often the user) may be watching it, or a job may be mid-run. `send-keys`
  types into wherever the pane cursor sits, so a command sent into an active or
  attached pane interleaves with what's already there and can corrupt both.
- **So observe before you send, and when unsure, ask.** Read the freshly-armed log
  (or, only if reading the pane is permitted in this environment, peek it) to learn
  the session's state first. If it's attached, running a job, or otherwise not
  idle at a clean prompt, stop and ask the user before sending anything rather than
  barging in.
---

## 2. Interacting

The strict driver form — and the only form this skill recommends:

```
tmux send-keys -t <name> "<command>" Enter
```

Three rules go with it:

- **Always end with `Enter`.** That's the tmux key name (capital E), not the
  literal word "Enter". Without it the command sits at the prompt unsent.
- **One command at a time.** After sending, observe completion *before* sending
  the next. Don't queue commands by sending several in a row — they'll
  concatenate or interleave with output.
- **To observe, read only the new tail of the log — not the whole file.**
  `$LOG_CURSOR` (the inline context variable from §1) holds the log's line count
  as of the last command. Sending and reading are **separate tool calls** — on
  Windows the send goes through WSL and the read through PowerShell, so they cannot
  share a command line; never append the read onto the send. The loop per command:

  1. Just before sending, note the current line count — this becomes `$LOG_CURSOR`.
     - Windows (PowerShell): `@(Get-Content $WIN_LOG).Count`
     - Linux: `wc -l < $WSL_SAVE_DIR/<name>.log`
  2. Send (its own call): `wsl -e bash -lc "tmux send-keys -t <name> '<command>' Enter"`
     (on Linux, the bare `tmux send-keys …`).
  3. After waiting, in a **second** call (never appended to the send) read just this
     command's reply (lines past the cursor) and the new count:
     - Windows (PowerShell): `$l = Get-Content $WIN_LOG; $l | Select-Object -Skip $LOG_CURSOR; '---'; $l.Count`
     - Linux: `tail -n +$(($LOG_CURSOR+1)) $WSL_SAVE_DIR/<name>.log; echo ---; wc -l < $WSL_SAVE_DIR/<name>.log`
  4. Update `$LOG_CURSOR` to the printed count for the next command.

  Plug in the literal `N` you hold in context. The command is done when that fresh
  segment ends with a returned prompt (e.g. `[user@host ~]$` with nothing typed
  after it); if it's still running, wait and re-read. A short `sleep 1` covers
  near-instant commands; longer jobs need a longer wait or a polling loop. Reading
  from the cursor keeps each read O(reply) however large the log has grown. If a
  check needs more than the latest reply, read a wider window — start from an
  earlier line number than `$LOG_CURSOR` to pull in more of the log; the cursor is
  the default start, not a ceiling.

- **Backup — when the log file itself is unavailable** (not yet armed, missing, or
  deleted): on Windows, `capture-pane` is **never** a read substitute (it runs
  through WSL — the rule is absolute). Instead rebuild the log from the pane buffer
  with `capture-pane`/`save-buffer` as a one-off control command (§3), re-arm
  `pipe-pane`, then resume reading the file with PowerShell `Get-Content`. On Linux
  you may peek directly:

  ```
  tmux capture-pane -t <name> -p | tail -10
  ```

  This is bounded by `history-limit`, so it shows only what's still in the pane
  buffer; re-arm `pipe-pane` (§3) to restore the primary channel.

**Why strict?** `send-keys` types the literal characters into wherever the
pane's cursor is sitting. If a previous command hasn't finished, or wasn't
terminated with `Enter`, the new text concatenates onto it — e.g. you can end
up with `[user@host ~]$echo hello` (no space between `$` and `echo`) because
the second send started typing into the still-active prompt line. Observing
before sending is the cheapest way to keep this from corrupting your commands.

---

## 3. Log — the primary read channel

The `pipe-pane` log armed in §1 is how you read the pane. It streams every byte
the pane emits into `$WSL_SAVE_DIR/<name>.log` continuously (until you stop it — run
`tmux pipe-pane -t <name>` again with no command), and it beats `capture-pane` as
the primary channel for two reasons: it has **no `history-limit` ceiling** (it
keeps output that has already scrolled past the pane buffer), and paired with the
cursor it gives precise, cheap per-command reads.

**The cursor.** `$LOG_CURSOR` is an inline context variable Claude holds (same
discipline as `$SCOPE_ROOT`): the log's line count as of the last command. Read a
reply with `Get-Content $WIN_LOG | Select-Object -Skip $LOG_CURSOR` on Windows
(PowerShell, never WSL) or `tail -n +$(($LOG_CURSOR+1))` on Linux, and advance the
cursor each round (§2). Because you only ever skip past the cursor, you process
O(reply) lines no matter how big the file is.

**Keeping it from growing without bound.** The cursor makes *reading* independent
of length; rotation bounds *disk*. Rotate when the log gets long — **~2000 lines**
is a good cap, anchored to the Read tool's 2000-line default so a whole-file
backup read fits one call, and far under the 50000-line `history-limit`. The check
reuses the line count you already read for the cursor — PowerShell on Windows, `wc -l`
on Linux. The truncation itself is a management *write*, not a content read, so it
stays in WSL even on Windows (the same `: >` keeps the inode `pipe-pane` writes to):

- Windows: read `@(Get-Content $WIN_LOG).Count` (PowerShell); if `> 2000`, truncate
  with `wsl -e bash -lc ': > $WSL_SAVE_DIR/<name>.log'` and reset `$LOG_CURSOR = 0`.
- Linux: `[ $(wc -l < $WSL_SAVE_DIR/<name>.log) -gt 2000 ] && : > $WSL_SAVE_DIR/<name>.log`

How you rotate matters, because `pipe-pane`'s `cat >> file` holds the file open in
append mode:

- **Truncate in place** (`: > $WSL_SAVE_DIR/<name>.log`, or `truncate -s 0`) keeps the
  **same inode**, so `pipe-pane` keeps writing with no gap. Lightest; use it when
  you don't need the old lines. Reset `$LOG_CURSOR = 0`.
- **Rotate keeping history:** stop `pipe-pane` (`tmux pipe-pane -t <name>` with no
  command), `mv $WSL_SAVE_DIR/<name>.log $WSL_SAVE_DIR/<name>.log.1`, then start `pipe-pane`
  again to recreate the file. Brief logging gap. Reset `$LOG_CURSOR = 0`. (A bare
  `mv` without restarting does **not** work: `cat`'s open handle follows the inode
  to the renamed file, so the original path is never recreated.)

**Backup — capture-pane, and the "log deleted" case.** If the log file is missing,
do **not** read with `capture-pane` on Windows (it runs through WSL and is never a
read path) — it is only a control command to rebuild the file. Note the trap:
**deleting the log with `rm` does not stop `pipe-pane`** — `cat`'s handle points at
the now-orphaned inode, so output is written to nowhere and the on-disk file never
reappears. If a log vanishes, **re-arm** `pipe-pane` (stop it, then start it again to
create a fresh file) and reset `$LOG_CURSOR = 0`. To rebuild a log from what is still
in the pane buffer, dump the scrollback once (a control command, in WSL on Windows),
then resume reading the file with PowerShell `Get-Content`:

```
tmux capture-pane -t <name> -S - ; tmux save-buffer <name>.log
```

**Scrollback caveat (backup only).** The `capture-pane` backup can't recover
anything that scrolled past `history-limit`; the streamed log has no such ceiling
— another reason it's the primary channel.

On Windows, only the *control* commands here (`pipe-pane`, `capture-pane`,
`save-buffer`, truncation/rotation writes) run via `wsl -e bash -lc '<cmd>'` with WSL
paths; **reading the log is always PowerShell `Get-Content` on the Windows path
`$WIN_LOG`, never WSL** (see the send/read split in the intro).

---

## 4. Other tmux knowledge

Commands that come up but aren't part of the core loop:

| Need | Command |
| --- | --- |
| List sessions | `tmux ls` |
| Attach (so the user can watch live) | `tmux attach -t <name>` |
| Detach from inside an attached session | `Ctrl-b d` |
| Backup: peek the visible pane | `tmux capture-pane -t <name> -p` |
| Raise scrollback | `tmux set -t <name> history-limit 50000` |
| Kill a session | `tmux kill-session -t <name>` |
| Tmux version | `tmux -V` |
| Built-in help | `tmux --help` |

When in doubt about a flag or subcommand, run `tmux --help` first — the local
build's syntax is the ground truth.

**On Windows** `tmux` is the real Linux build running inside WSL — every command in
this table is a tmux *control* command, so it runs wrapped in `wsl -e bash -lc '...'`.
The one thing **not** in this table is reading the log: that is always PowerShell
`Get-Content` on `$WIN_LOG`, never WSL (and `capture-pane` is not a read path). See
the send/read split in the intro.

---

## 5. Pattern: SSH-in-tmux (use as a remote terminal)

A common reason to use this skill is to drive a remote host that Claude can't
reach directly (no MCP, no agent on the far side, possibly no internet from
there outward). The trick is to put the SSH connection *inside* the tmux
session: tmux holds the local end of the pipe, and `send-keys` (to write) plus the
streamed log read back with `Get-Content` (on Windows; `tail` on Linux) become your
way of talking to the remote shell.

The setup is one extra command after Init:

```
tmux send-keys -t <name> "ssh <host>" Enter
```

`<host>` should be an alias defined in `~/.ssh/config` so authentication relies
on the user's key/agent — never put a password into `send-keys`. Wait for the
remote prompt to appear (observe per Section 2: read the log tail from the cursor —
PowerShell `Get-Content` on Windows — and look for `user@remote:~$` or similar)
before issuing any remote command.

After that, **nothing changes**. Every remote command is the same form as a
local one:

```
tmux send-keys -t <name> "ls /scratch" Enter
```

…and the log and cursor see the remote output the same way they saw local output —
the SSH session is just bytes flowing through the pane, read the same way (PowerShell
`Get-Content` on Windows, never WSL).

When use a remote shell, remember the scope policy work on it. Use an inline context variable $REMOTE_SCOPE_ROOT in Claude code.

Because that SSH shell lives inside the persistent tmux pane, remote shell state
survives between tool calls (unlike a fresh local shell): an `export` on the
remote — e.g. a working-scope variable `export REMOTE_SCOPE_ROOT=<path>` —
persists across later commands, a handy way to pin a remote scope. Still hold
the value as context policy and self-check against it; don't rely on the shell
to enforce it. Also,defining other remote shell variables if it will be useful.

To disconnect, send `exit` (returns to the local shell, session stays alive) or
`tmux kill-session -t <name>` to tear it all down. If the SSH connection drops,
send another `ssh <host>` into the same pane to reconnect; the session and any
local state Claude has built up (log file, state files) are preserved.

**Subagent-opened SSH sessions — close on exit.** A subagent's own SSH-in-tmux session
(named per §1, `<server>_<task>_Sub_<subagent_task>`) is owned by that subagent for its
lifetime only — as its **final step (on success *or* error)** run `tmux kill-session -t
<name>` so no orphaned SSH sessions or log files are left behind. Keep it open past the
subagent only when the task explicitly needs the parent to inherit it.


