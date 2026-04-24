#!/usr/bin/env python3
"""session-analyzer — Parse, extract, and analyze Claude Code session JSONL files.

Zero external dependencies. Python 3.10+ required.

Usage:
    session-analyzer.py list    [--project PATH] [--since DATE] [--before DATE]
                                [--min-size SIZE] [--latest] [--json] [-n LIMIT]
    session-analyzer.py search  <query> [--project PATH] [-n LIMIT]
    session-analyzer.py extract <file.jsonl> [-o PATH] [--head N] [--tail N]
                                [--tools] [--thinking] [--timestamps]
    session-analyzer.py analyze <file.jsonl> [--format json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"


# ── parsing helpers ──────────────────────────────────────────────────


def parse_date(s: str) -> datetime:
    """Parse a human-friendly date string into a datetime.

    Supports: YYYY-MM-DD, 'today', 'yesterday', relative (3d, 2w, 6h).
    """
    s = s.lower().strip()
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if s == "today":
        return midnight
    if s == "yesterday":
        return midnight - timedelta(days=1)
    m = re.match(r"^(\d+)([dhw])$", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        deltas = {"d": timedelta(days=n), "h": timedelta(hours=n), "w": timedelta(weeks=n)}
        return now - deltas[unit]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Can't parse date: {s!r}. Use YYYY-MM-DD, 'today', 'yesterday', or Nd/Nw/Nh"
        )


def parse_size(s: str) -> int:
    """Parse a human-friendly size string (e.g., '1M', '500K') into bytes."""
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$", s.upper().strip())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Can't parse size: {s!r}. Use e.g., 500K, 1M, 5M"
        )
    n = float(m.group(1))
    mult = {"": 1, "K": 1024, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
    return int(n * mult[m.group(2)])


def fmt_size(sz: int) -> str:
    """Format byte count as human-readable string."""
    if sz >= 1 << 20:
        return f"{sz / (1 << 20):.1f} MB"
    if sz >= 1024:
        return f"{sz / 1024:.0f} KB"
    return f"{sz} B"


def slugify(s: str) -> str:
    """Convert a string to a filesystem-safe slug."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:60].rstrip("-")


# ── JSONL streaming ──────────────────────────────────────────────────


def stream_jsonl(filepath: str):
    """Yield parsed JSON objects from a JSONL file, one per line."""
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def scan_metadata(filepath: str) -> dict:
    """Quick scan for session metadata: id, name, start time."""
    session_id: str | None = None
    first_ts: str | None = None
    session_name: str | None = None

    for entry in stream_jsonl(filepath):
        if not session_id and entry.get("sessionId"):
            session_id = entry["sessionId"]
        if not first_ts and entry.get("timestamp"):
            first_ts = entry["timestamp"]
        if entry.get("type") == "custom-title":
            session_name = entry.get("customTitle")
        if session_id and first_ts and session_name:
            break

    if not session_name:
        for entry in stream_jsonl(filepath):
            if entry.get("type") == "custom-title":
                session_name = entry.get("customTitle")
                break

    return {
        "session_id": session_id or Path(filepath).stem,
        "first_ts": first_ts,
        "session_name": session_name,
    }


# ── content helpers ──────────────────────────────────────────────────


def extract_text(content) -> str:
    """Pull plain text from message content (string or content-block array)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def extract_thinking(content) -> str | None:
    """Pull thinking text from an assistant content array."""
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict) and block.get("type") == "thinking":
            return block.get("thinking")
    return None


def extract_tool_uses(content) -> list[dict]:
    """Pull tool_use blocks from an assistant content array."""
    if not isinstance(content, list):
        return []
    return [
        {
            "name": b.get("name", "unknown"),
            "input": b.get("input", {}),
        }
        for b in content
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]


def fmt_time(ts: str) -> str:
    """ISO timestamp → '1:07:32 PM' (12-hour clock)."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        h = dt.hour % 12 or 12
        return f"{h}:{dt.minute:02d}:{dt.second:02d} {'AM' if dt.hour < 12 else 'PM'}"
    except (ValueError, AttributeError):
        return ts or ""


def summarize_tool(name: str, inp: dict) -> str:
    """One-line summary of a tool call's input."""
    if name in ("Read", "Write", "Edit"):
        return inp.get("file_path", "")
    if name == "Bash":
        cmd = inp.get("command", "")
        return (cmd[:120] + "…") if len(cmd) > 120 else cmd
    if name in ("Grep", "Glob"):
        return f"{inp.get('pattern', '')} in {inp.get('path', '')}"
    if name == "Agent":
        return inp.get("description", "")[:80]
    if name == "Skill":
        return inp.get("skill", "")
    if name == "WebSearch":
        return inp.get("query", "")[:80]
    if name == "WebFetch":
        return inp.get("url", "")[:80]
    if name == "SendMessage":
        return f"to={inp.get('to', '?')}"
    if name == "TaskCreate":
        return inp.get("description", "")[:60]
    raw = json.dumps(inp, ensure_ascii=False)
    return (raw[:100] + "…") if len(raw) > 100 else raw


# ── project resolution ───────────────────────────────────────────────


def resolve_project_dir(project: str | None) -> Path | None:
    """Resolve a project path to its Claude sessions directory."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return None
    if project:
        dir_name = project.rstrip("/").replace("/", "-")
        if not dir_name.startswith("-"):
            dir_name = "-" + dir_name
        d = projects_dir / dir_name
        return d if d.is_dir() else None
    return None


def list_all_project_dirs() -> list[Path]:
    """Return all project directories that contain JSONL session files."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []
    return sorted(
        d for d in projects_dir.iterdir()
        if d.is_dir() and any(d.glob("*.jsonl"))
    )


def collect_sessions(
    project_dir: Path,
    *,
    since: datetime | None = None,
    before: datetime | None = None,
    min_size: int | None = None,
    limit: int = 20,
) -> list[Path]:
    """Collect and filter session files from a project directory."""
    sessions = list(project_dir.glob("*.jsonl"))
    if since:
        sessions = [s for s in sessions if datetime.fromtimestamp(s.stat().st_mtime) >= since]
    if before:
        sessions = [s for s in sessions if datetime.fromtimestamp(s.stat().st_mtime) < before]
    if min_size:
        sessions = [s for s in sessions if s.stat().st_size >= min_size]
    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions[:limit]


# ── extract ──────────────────────────────────────────────────────────


def _build_output_path(args: argparse.Namespace, meta: dict) -> Path | None:
    """Determine the output file path for extract.

    Returns None when --head or --tail is set (stdout preview mode).
    """
    if args.head or args.tail:
        return None

    date_str = "undated"
    if meta["first_ts"]:
        try:
            dt = datetime.fromisoformat(meta["first_ts"].replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    name_part = slugify(meta["session_name"]) if meta["session_name"] else meta["session_id"][:8]
    filename = f"transcript-{date_str}-{name_part}.md"

    if args.output:
        p = Path(args.output)
        if p.is_dir():
            return p / filename
        return p

    return Path("/tmp") / filename


def _render_turn(
    role: str,
    text: str,
    ts: str,
    *,
    show_timestamps: bool,
    thinking: str | None = None,
    show_thinking: bool = False,
    tool_calls: list[dict] | None = None,
    show_tools: bool = False,
) -> list[str]:
    """Render a single conversation turn as markdown lines."""
    lines: list[str] = []
    tag = f" `{fmt_time(ts)}`" if show_timestamps and ts else ""

    if show_thinking and thinking and thinking.strip():
        lines.append("\n<details><summary>Thinking</summary>\n")
        lines.append(thinking.strip())
        lines.append("\n</details>")

    if show_tools and tool_calls:
        for tool in tool_calls:
            summary = summarize_tool(tool["name"], tool["input"])
            lines.append(f"> **{tool['name']}** — `{summary}`")

    if text.strip():
        lines.append(f"\n## {role}{tag}\n")
        lines.append(text)

    return lines


def _collect_turns(args: argparse.Namespace) -> list[list[str]]:
    """Stream through the JSONL and collect rendered turns."""
    turns: list[list[str]] = []

    for entry in stream_jsonl(args.file):
        if entry.get("isSidechain") and not args.sidechains:
            continue

        etype = entry.get("type")
        ts = entry.get("timestamp", "")

        if etype == "user":
            msg = entry.get("message", {})
            if msg.get("role") != "user":
                continue
            text = extract_text(msg.get("content", ""))
            if not text.strip():
                continue
            rendered = _render_turn(
                "User", text, ts, show_timestamps=args.timestamps,
            )
            if rendered:
                turns.append(rendered)

        elif etype == "assistant":
            msg = entry.get("message", {})
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", [])
            text = extract_text(content)
            thinking = extract_thinking(content) if args.thinking else None
            tool_calls = extract_tool_uses(content) if args.tools else None
            rendered = _render_turn(
                "Assistant", text, ts,
                show_timestamps=args.timestamps,
                thinking=thinking,
                show_thinking=args.thinking,
                tool_calls=tool_calls,
                show_tools=args.tools,
            )
            if rendered:
                turns.append(rendered)

    return turns


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract a human-readable conversation transcript."""
    meta = scan_metadata(args.file)
    output_path = _build_output_path(args, meta)
    preview_mode = args.head or args.tail

    turns = _collect_turns(args)

    if args.head:
        turns = turns[: args.head]
    elif args.tail:
        turns = turns[-args.tail :]

    if preview_mode:
        out = sys.stdout
    else:
        out = open(str(output_path), "w", encoding="utf-8")

    def emit(text: str = "") -> None:
        print(text, file=out)

    if not preview_mode:
        emit(f"# Session Transcript — {meta['session_name'] or meta['session_id'][:12]}\n")
        if meta["first_ts"]:
            emit(f"**Date:** {meta['first_ts']}")
        emit(f"**Source:** `{Path(args.file).name}`\n")
        emit("---")

    for turn_lines in turns:
        for line in turn_lines:
            emit(line)

    if not preview_mode:
        out.close()
        print(str(output_path))


# ── analyze ──────────────────────────────────────────────────────────


def cmd_analyze(args: argparse.Namespace) -> None:
    """Compute and display session statistics."""
    type_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()
    models: set[str] = set()
    branches: set[str] = set()
    versions: set[str] = set()
    timestamps: list[datetime] = []
    files_modified: set[str] = set()
    session_name: str | None = None

    user_msgs = 0
    assistant_turns = 0
    thinking_blocks = 0
    input_tok = output_tok = cache_read = cache_create = 0

    for entry in stream_jsonl(args.file):
        etype = entry.get("type", "unknown")
        type_counts[etype] += 1

        ts = entry.get("timestamp")
        if ts:
            try:
                timestamps.append(
                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
                )
            except ValueError:
                pass

        if entry.get("gitBranch"):
            branches.add(entry["gitBranch"])
        if entry.get("version"):
            versions.add(entry["version"])
        if etype == "custom-title" and entry.get("customTitle"):
            session_name = entry["customTitle"]

        if etype == "user":
            msg = entry.get("message", {})
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    user_msgs += 1
                elif isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "text"
                    for b in content
                ):
                    user_msgs += 1

        elif etype == "assistant":
            assistant_turns += 1
            msg = entry.get("message", {})
            model = msg.get("model")
            if model:
                models.add(model)

            usage = msg.get("usage", {})
            input_tok += usage.get("input_tokens", 0)
            output_tok += usage.get("output_tokens", 0)
            cache_read += usage.get("cache_read_input_tokens", 0)
            cache_create += usage.get("cache_creation_input_tokens", 0)

            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "thinking":
                    thinking_blocks += 1
                elif block.get("type") == "tool_use":
                    tool_counts[block.get("name", "unknown")] += 1
                    inp = block.get("input", {})
                    if block.get("name") in ("Write", "Edit"):
                        fp = inp.get("file_path")
                        if fp:
                            files_modified.add(fp)

    # duration
    dur = "—"
    if len(timestamps) >= 2:
        secs = int((timestamps[-1] - timestamps[0]).total_seconds())
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        dur = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")

    total_in = input_tok + cache_read
    cache_pct = f"{cache_read / total_in * 100:.1f}%" if total_in else "—"

    if args.format == "json":
        print(
            json.dumps(
                {
                    "file": args.file,
                    "session_name": session_name,
                    "duration": dur,
                    "start": timestamps[0].isoformat() if timestamps else None,
                    "end": timestamps[-1].isoformat() if timestamps else None,
                    "models": sorted(models),
                    "branches": sorted(branches),
                    "harness_versions": sorted(versions),
                    "user_messages": user_msgs,
                    "assistant_turns": assistant_turns,
                    "thinking_blocks": thinking_blocks,
                    "tokens": {
                        "input": input_tok,
                        "output": output_tok,
                        "cache_read": cache_read,
                        "cache_create": cache_create,
                        "cache_hit_rate": cache_pct,
                    },
                    "tool_calls": dict(tool_counts.most_common()),
                    "total_tool_calls": sum(tool_counts.values()),
                    "files_modified": sorted(files_modified),
                    "entry_types": dict(type_counts.most_common()),
                },
                indent=2,
            )
        )
        return

    # ── markdown output ──
    title = session_name or Path(args.file).stem[:12]
    print(f"# Session Analysis — {title}\n")
    print("| | |")
    print("|---|---|")
    if session_name:
        print(f"| **Name** | {session_name} |")
    print(f"| **Duration** | {dur} |")
    if timestamps:
        print(f"| **Start** | {timestamps[0].isoformat()} |")
        print(f"| **End** | {timestamps[-1].isoformat()} |")
    print(f"| **Model(s)** | {', '.join(sorted(models)) or '—'} |")
    print(f"| **Branch(es)** | {', '.join(sorted(branches)) or '—'} |")
    print(f"| **Harness** | {', '.join(sorted(versions)) or '—'} |")

    print("\n## Conversation\n")
    print("| Metric | Count |")
    print("|--------|------:|")
    print(f"| User messages | {user_msgs} |")
    print(f"| Assistant turns | {assistant_turns} |")
    print(f"| Thinking blocks | {thinking_blocks} |")

    print("\n## Tokens\n")
    print("| Metric | Count |")
    print("|--------|------:|")
    print(f"| Input | {input_tok:,} |")
    print(f"| Output | {output_tok:,} |")
    print(f"| Cache read | {cache_read:,} |")
    print(f"| Cache create | {cache_create:,} |")
    print(f"| Cache hit rate | {cache_pct} |")
    print(f"| **Total (in+out)** | **{input_tok + output_tok:,}** |")

    if tool_counts:
        total = sum(tool_counts.values())
        print(f"\n## Tools — {total} calls\n")
        print("| Tool | Calls |")
        print("|------|------:|")
        for name, count in tool_counts.most_common():
            print(f"| {name} | {count} |")

    if files_modified:
        print(f"\n## Files Modified — {len(files_modified)}\n")
        for f in sorted(files_modified):
            print(f"- `{f}`")

    print("\n## Entry Types\n")
    print("| Type | Count |")
    print("|------|------:|")
    for t, c in type_counts.most_common():
        print(f"| {t} | {c} |")


# ── list ─────────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    """List available session JSONL files with optional filters."""
    since = parse_date(args.since) if args.since else None
    before = parse_date(args.before) if args.before else None
    min_size = parse_size(args.min_size) if args.min_size else None

    if args.project:
        project_dir = resolve_project_dir(args.project)
        if not project_dir:
            print("Project not found. Available:", file=sys.stderr)
            for d in list_all_project_dirs():
                print(f"  {d.name}", file=sys.stderr)
            sys.exit(1)
        _list_project(
            project_dir, args.project,
            since=since, before=before, min_size=min_size,
            limit=args.limit, as_json=args.json, latest=args.latest,
        )
    else:
        if args.latest:
            print("--latest requires --project", file=sys.stderr)
            sys.exit(1)
        _list_all_projects(since=since, before=before, min_size=min_size, as_json=args.json)


def _list_project(
    project_dir: Path,
    project_label: str,
    *,
    since: datetime | None,
    before: datetime | None,
    min_size: int | None,
    limit: int,
    as_json: bool,
    latest: bool,
) -> None:
    sessions = collect_sessions(
        project_dir, since=since, before=before, min_size=min_size, limit=limit,
    )
    if not sessions:
        print("No matching sessions.", file=sys.stderr)
        sys.exit(1)

    if latest:
        print(str(sessions[0]))
        return

    if as_json:
        rows = []
        for s in sessions:
            stat = s.stat()
            rows.append({
                "path": str(s),
                "session_id": s.stem,
                "size": stat.st_size,
                "size_human": fmt_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        print(json.dumps(rows, indent=2))
        return

    print(f"# Sessions — {project_label}\n")
    print("| # | Session | Size | Modified | Path |")
    print("|--:|---------|-----:|----------|------|")
    for i, s in enumerate(sessions, 1):
        stat = s.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %I:%M %p")
        print(f"| {i} | `{s.stem[:12]}…` | {fmt_size(stat.st_size)} | {mtime} | `{s}` |")


def _list_all_projects(
    *,
    since: datetime | None,
    before: datetime | None,
    min_size: int | None,
    as_json: bool,
) -> None:
    dirs = list_all_project_dirs()
    if not dirs:
        print("No projects with sessions found.", file=sys.stderr)
        sys.exit(1)

    if as_json:
        rows = []
        for d in dirs:
            sessions = collect_sessions(d, since=since, before=before, min_size=min_size, limit=9999)
            if not sessions:
                continue
            latest_stat = sessions[0].stat()
            rows.append({
                "project_dir": d.name,
                "path": str(d),
                "session_count": len(sessions),
                "latest_modified": datetime.fromtimestamp(latest_stat.st_mtime).isoformat(),
                "latest_session": str(sessions[0]),
            })
        print(json.dumps(rows, indent=2))
        return

    print("# Projects with Sessions\n")
    print("| Project | Sessions | Latest |")
    print("|---------|--------:|--------|")
    for d in dirs:
        sessions = collect_sessions(d, since=since, before=before, min_size=min_size, limit=9999)
        if not sessions:
            continue
        mtime = datetime.fromtimestamp(sessions[0].stat().st_mtime).strftime(
            "%Y-%m-%d %I:%M %p"
        )
        print(f"| `{d.name}` | {len(sessions)} | {mtime} |")
    print("\nUse `--project /path/to/repo` to list sessions for a specific project.")


# ── search ───────────────────────────────────────────────────────────


def cmd_search(args: argparse.Namespace) -> None:
    """Search for text across session JSONL files."""
    query_lower = args.query.lower()

    if args.project:
        project_dir = resolve_project_dir(args.project)
        if not project_dir:
            print("Project not found.", file=sys.stderr)
            sys.exit(1)
        session_files = sorted(
            project_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    else:
        session_files = []
        for d in list_all_project_dirs():
            session_files.extend(d.glob("*.jsonl"))
        session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    total_hits = 0
    results: list[dict] = []

    for sf in session_files:
        if total_hits >= args.limit:
            break
        hits = _search_session(sf, query_lower, args.limit - total_hits, args.context)
        if hits:
            results.append({"file": str(sf), "session_id": sf.stem, "hits": hits})
            total_hits += len(hits)

    if not results:
        print(f'No matches for "{args.query}".', file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(f'# Search: "{args.query}" — {total_hits} match{"es" if total_hits != 1 else ""}\n')
    for r in results:
        print(f"## `{r['session_id'][:12]}…`\n")
        print(f"**File:** `{r['file']}`\n")
        for hit in r["hits"]:
            role = hit["role"].capitalize()
            ts = fmt_time(hit["timestamp"]) if hit["timestamp"] else ""
            ts_tag = f" `{ts}`" if ts else ""
            print(f"**{role}**{ts_tag}:")
            print(f"> {hit['snippet']}\n")


def _search_session(
    filepath: Path, query_lower: str, max_hits: int, context_chars: int
) -> list[dict]:
    """Search a single session file for matching text. Returns hit dicts."""
    hits: list[dict] = []
    for entry in stream_jsonl(str(filepath)):
        if len(hits) >= max_hits:
            break
        etype = entry.get("type")
        if etype not in ("user", "assistant"):
            continue
        msg = entry.get("message", {})
        role = msg.get("role", etype)
        content = msg.get("content", "")
        text = extract_text(content)
        if not text:
            continue
        text_lower = text.lower()
        idx = text_lower.find(query_lower)
        if idx == -1:
            continue
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(query_lower) + context_chars)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet = snippet + "…"
        hits.append({
            "role": role,
            "timestamp": entry.get("timestamp", ""),
            "snippet": snippet,
        })
    return hits


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="session-analyzer",
        description="Parse, extract, and analyze Claude Code session JSONL files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
argument hints (common queries → flags):
  "last session"            list --latest --project <path>
  "yesterday's sessions"    list --since yesterday --project <path>
  "big sessions"            list --min-size 5M --project <path>
  "sessions this week"      list --since 7d --project <path>
  "find where we discussed" search "topic" --project <path>
  "full transcript"         extract <file>
  "peek at the start"       extract <file> --head 10
  "what was the last thing"  extract <file> --tail 5
  "with tool calls"         extract <file> --tools --timestamps
  "token usage"             analyze <file>
  "machine-readable"        list --json / analyze --format json
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── list ──
    p_lst = sub.add_parser(
        "list",
        help="List session files with filtering",
        description="Find sessions by date, size, or project. Use --latest for the most recent path.",
    )
    p_lst.add_argument("-p", "--project", help="Project repo path (e.g., /Users/me/repo)")
    p_lst.add_argument(
        "--since",
        help="Sessions modified on/after DATE (YYYY-MM-DD, today, yesterday, Nd, Nw, Nh)",
    )
    p_lst.add_argument(
        "--before",
        help="Sessions modified before DATE (same formats as --since)",
    )
    p_lst.add_argument(
        "--min-size",
        help="Minimum file size (e.g., 500K, 1M, 5M)",
    )
    p_lst.add_argument(
        "--latest",
        action="store_true",
        help="Output only the most recent session's full path (requires --project)",
    )
    p_lst.add_argument(
        "--json", action="store_true", help="JSON output with full paths",
    )
    p_lst.add_argument(
        "-n", "--limit", type=int, default=20, help="Max sessions to show (default: 20)",
    )
    p_lst.set_defaults(func=cmd_list)

    # ── search ──
    p_srch = sub.add_parser(
        "search",
        help="Search session content for keywords",
        description="Case-insensitive text search across session conversations.",
    )
    p_srch.add_argument("query", help="Text to search for")
    p_srch.add_argument("-p", "--project", help="Limit search to this project")
    p_srch.add_argument(
        "-n", "--limit", type=int, default=10, help="Max matches to return (default: 10)",
    )
    p_srch.add_argument(
        "-c", "--context", type=int, default=80, help="Characters of context around match (default: 80)",
    )
    p_srch.add_argument(
        "--json", action="store_true", help="JSON output",
    )
    p_srch.set_defaults(func=cmd_search)

    # ── extract ──
    p_ext = sub.add_parser(
        "extract",
        help="Extract readable conversation transcript",
        description=(
            "Export a clean markdown transcript. Saves to a temp file by default "
            "(prints the path). Use -o to specify a directory or filename. "
            "Use --head/--tail to preview turns in stdout without saving."
        ),
    )
    p_ext.add_argument("file", help="Path to session JSONL file")
    p_ext.add_argument(
        "-o", "--output",
        help="Output path: a directory (auto-names the file) or a full filepath",
    )
    p_ext.add_argument(
        "--head", type=int, metavar="N",
        help="Preview first N turns to stdout (no file saved)",
    )
    p_ext.add_argument(
        "--tail", type=int, metavar="N",
        help="Preview last N turns to stdout (no file saved)",
    )
    p_ext.add_argument(
        "-t", "--tools", action="store_true", help="Include tool-call summaries",
    )
    p_ext.add_argument(
        "--thinking", action="store_true", help="Include thinking blocks",
    )
    p_ext.add_argument(
        "--timestamps", action="store_true", help="Show timestamps per turn",
    )
    p_ext.add_argument(
        "--sidechains",
        action="store_true",
        help="Include sidechain (sub-agent) entries",
    )
    p_ext.set_defaults(func=cmd_extract)

    # ── analyze ──
    p_ana = sub.add_parser(
        "analyze",
        help="Show session statistics",
        description="Token usage, tool breakdown, duration, files modified.",
    )
    p_ana.add_argument("file", help="Path to session JSONL file")
    p_ana.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_ana.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
