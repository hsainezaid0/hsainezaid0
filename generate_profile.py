#!/usr/bin/env python3
"""Build self-contained GitHub profile SVGs from public GitHub data (stdlib only)."""

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import re
import textwrap
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT
MINT, CYAN, VIOLET, TEXT, MUTED = "#54efb5", "#65d8ff", "#b597ff", "#eef6ff", "#91a5ba"
QUERY = """
query Profile($login:String!, $cursor:String) {
  user(login:$login) {
    repositories(first:100, after:$cursor, privacy:PUBLIC, ownerAffiliations:[OWNER]) {
      totalCount
      nodes {
        name isFork stargazerCount description url pushedAt homepageUrl
        forks { totalCount }
        languages(first:100, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
          pageInfo { hasNextPage }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def fetch_public_data(login, token):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise ValueError("Invalid GitHub username")
    cursor, repositories, calendar, repo_count = None, [], None, 0
    while True:
        body = json.dumps({"query": QUERY, "variables": {"login": login, "cursor": cursor}}).encode()
        req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "github-profile-svg-generator",
        })
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"GitHub returned HTTP {exc.code}; existing assets have been preserved") from None
        if result.get("errors"):
            raise RuntimeError("GitHub GraphQL: " + "; ".join(e["message"] for e in result["errors"]))
        user = result.get("data", {}).get("user")
        if not user:
            raise RuntimeError("GitHub user not found")
        connection = user["repositories"]
        repo_count = connection["totalCount"]
        repositories.extend(connection["nodes"])
        calendar = calendar or user["contributionsCollection"]["contributionCalendar"]
        if not connection["pageInfo"]["hasNextPage"]:
            break
        new_cursor = connection["pageInfo"]["endCursor"]
        if not new_cursor or new_cursor == cursor:
            raise RuntimeError("GitHub pagination did not advance")
        cursor = new_cursor
    sizes, colors = Counter(), {}
    for repo in repositories:
        if repo["isFork"] or repo["name"].lower() == login.lower():
            continue
        if repo["languages"]["pageInfo"]["hasNextPage"]:
            raise RuntimeError("A repository has more than 100 languages; refusing incomplete statistics")
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] += edge["size"]
            colors[name] = edge["node"]["color"] or CYAN
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    projects = []
    for repo in repositories:
        if repo["isFork"] or repo["name"].lower() == login.lower():
            continue
        edges = repo["languages"]["edges"]
        byte_count = sum(edge["size"] for edge in edges)
        primary = edges[0] if edges else None
        projects.append({
            "name": repo["name"], "description": repo.get("description") or "",
            "url": repo["url"], "updated_at": repo.get("pushedAt") or "",
            "website": repo.get("homepageUrl") or "", "stars": repo["stargazerCount"],
            "forks": repo["forks"]["totalCount"],
            "language": primary["node"]["name"] if primary else None,
            "primary_share": 100*primary["size"]/byte_count if primary and byte_count else None,
            "language_shares": [{"name": e["node"]["name"], "percent": 100*e["size"]/byte_count} for e in edges] if byte_count else [],
        })
    return {
        "login": login,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "GitHub GraphQL public repositories and contribution calendar",
        "public_repositories": repo_count,
        "total_contributions": calendar["totalContributions"],
        "days": days,
        "languages": [{"name": n, "size": s, "color": colors[n]} for n, s in sizes.most_common()],
        "language_sync_pending": False,
        "projects": projects,
    }


def t(x, y, value, size=18, color=TEXT, weight=400, mono=False, extra=""):
    font = "'DejaVu Sans Mono',monospace" if mono else "'DejaVu Sans',sans-serif"
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill, rx=0, stroke="none", extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" {extra}/>'


def svg(w, h, title, body):
    defs = '''<defs>
      <linearGradient id="panel" x2="1" y2="1"><stop stop-color="#101f31"/><stop offset="1" stop-color="#08111e"/></linearGradient>
      <linearGradient id="accent"><stop stop-color="#54efb5"/><stop offset=".5" stop-color="#65d8ff"/><stop offset="1" stop-color="#b597ff"/></linearGradient>
      <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#21364a"/></pattern>
      <pattern id="scan" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M0 0H6" stroke="#fff" stroke-opacity=".025"/></pattern>
    </defs>'''
    css = '''<style>
      @keyframes blink {0%,45%,100%{opacity:1}50%,95%{opacity:.12}}
      @keyframes hover {0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
      @keyframes shot {from{transform:translateY(100px);opacity:0}20%{opacity:1}to{transform:translateY(-110px);opacity:0}}
      @keyframes fleet {0%,100%{transform:translateX(-10px)}50%{transform:translateX(10px)}}
      @keyframes knight {0%,35%,100%{transform:translate(0,0)}45%,80%{transform:translate(58px,-29px)}}
      .blink{animation:blink 2s infinite}.float{animation:hover 4s ease-in-out infinite}.shot{animation:shot 1.8s linear infinite}.fleet{animation:fleet 5s ease-in-out infinite}.knight{animation:knight 7s ease-in-out infinite}
      @media(prefers-reduced-motion:reduce){*{animation:none!important}}
    </style>'''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title"><title id="title">{escape(title)}</title>{defs}{css}{body}</svg>\n'


def panel(w, h, title, file):
    return (rect(1, 1, w-2, h-2, "url(#panel)", 20, "url(#accent)", 'stroke-opacity=".43"')
            + rect(1, 1, w-2, 47, "#101c2a", 20)
            + rect(2, 49, w-4, h-51, "url(#dots)", 18, extra='opacity=".13"')
            + ''.join(f'<circle cx="{25+i*17}" cy="25" r="4" fill="{c}"/>' for i, c in enumerate(["#ff6b89", "#ffcf67", MINT]))
            + t(88, 30, title, 13, MINT, 600, mono=True)
            + t(w-26, 30, file, 11, "#617c95", mono=True, extra='text-anchor="end"'))


def pill(x, y, label, color=MINT, size=13):
    w = len(label) * size * .64 + 25
    return rect(x, y, round(w), 29, "#12283a", 8, "#2a475a") + t(x+12, y+20, label, size, color, mono=True), w


def cat(x, y, scale=1):
    # Original pixel mascot, intentionally independent of any remote image service.
    rows = ["..##........##..", "..###......###..", "..####....####..", "..############..", ".##############.", ".###ee####ee###.", ".###ee####ee###.", ".###pp####pp###.", ".##############.", "..####nn#######.", "...###mm#####...", "....########....", "...##########...", "..############..", "..###.####.###..", "..###......###.."]
    colors = {"#": "#17283d", "e": MINT, "p": "#07101c", "n": "#ff7da7", "m": "#d86793"}
    out = f'<g transform="translate({x},{y}) scale({scale})" shape-rendering="crispEdges">'
    for yy, row in enumerate(rows):
        for xx, c in enumerate(row):
            if c in colors:
                out += rect(xx*8, yy*8, 8, 8, colors[c])
    return out + '</g>'


def banner(config):
    b = panel(1200, 350, "~/" + config["login"], "profile.init")
    b += rect(760, 49, 438, 298, "url(#dots)", 18)
    b += t(42, 91, "HELLO, WORLD. I'M", 14, MINT, mono=True)
    b += t(38, 158, config["name"].upper(), 61, TEXT, 700)
    b += rect(42, 180, 590, 3, "url(#accent)", 1)
    b += t(42, 219, config["role"], 22, TEXT)
    b += t(42, 252, config["education"], 16, MUTED)
    x = 42
    for label, color in [("CYBERSECURITY", MINT), ("ARTIFICIAL INTELLIGENCE", VIOLET)]:
        p, width = pill(x, 282, label, color)
        b += p
        x += width + 12
    b += '<g class="float">' + rect(840, 87, 264, 194, "#080f1b", 15, "#2a5367")
    b += cat(896, 104, 1.12) + t(866, 260, "> build. learn. repeat_", 13, MINT, mono=True) + '</g>'
    b += t(1130, 319, "01 / ONLINE", 11, MUTED, mono=True, extra='text-anchor="end"')
    return svg(1200, 350, config["name"] + " — " + config["role"], b)


def metrics(data):
    days = data["days"]
    active = sum(d["contributionCount"] > 0 for d in days)
    peak = max((d["contributionCount"] for d in days), default=0)
    b = panel(588, 340, "GITHUB / ACTIVITY", "stats.snapshot")
    values = [(data["public_repositories"], "PUBLIC REPOSITORIES", MINT),
              (data["total_contributions"], "CONTRIBUTIONS / 12 MONTHS", CYAN),
              (active, "ACTIVE DAYS / 12 MONTHS", VIOLET),
              (peak, "BUSIEST DAY", "#ffcf67")]
    for i, (value, label, color) in enumerate(values):
        x, y = 28 + (i % 2)*283, 68 + (i // 2)*113
        b += rect(x, y, 251, 99, "#0c1725", 12, "#21394e")
        b += t(x+18, y+49, f"{value:,}", 40, color, 700, True)
        b += t(x+18, y+78, label, 10, MUTED, mono=True)
    b += t(29, 318, "SNAPSHOT  " + data["updated_at"][:10] + "  /  GITHUB CALENDAR", 10, MUTED, mono=True)
    return svg(588, 340, "GitHub activity statistics", b)


def language_stack(data):
    b = panel(588, 340, "LANGUAGE STACK", "stack.scan")
    langs = data.get("languages", [])
    if data.get("language_sync_pending"):
        b += t(30, 101, "First scan pending", 25, VIOLET, 700)
        b += t(30, 134, "Public repository language scan", 13, MUTED)
        b += rect(30, 162, 528, 1, "#284055")
        b += t(30, 199, "$ language_scan --public", 15, MINT, mono=True)
        b += t(30, 230, "Byte-based percentages will appear", 15, TEXT)
        b += t(30, 256, "after the first GitHub Actions run.", 15, TEXT)
        b += t(30, 314, "SOURCE: PUBLIC REPOSITORY · SYNC PENDING", 10, MUTED, mono=True)
    elif not langs:
        b += t(30, 116, "Your next language starts here.", 23, TEXT, 700)
        b += t(30, 158, "Publish code to grow this stack.", 15, MUTED)
        b += t(30, 314, "FORKS AND PROFILE ASSETS EXCLUDED", 11, MUTED, mono=True)
    else:
        by_repo = data.get("language_measure") == "repositories"
        subtitle = "Primary language per public repository" if by_repo else "Public code · share of language bytes"
        b += t(30, 78, subtitle, 12, MUTED)
        total = sum(l["size"] for l in langs)
        groups = langs[:4]
        if len(langs) > 4:
            groups = groups + [{"name": "Other", "size": sum(l["size"] for l in langs[4:]), "color": MUTED}]
        for i, lang in enumerate(groups):
            y, ratio = 108+i*41, lang["size"]/max(1, total)
            name = lang["name"]
            if len(name) > 14:
                name = name[:13] + "…"
            b += f'<circle cx="35" cy="{y-4}" r="4" fill="{lang["color"]}"/>'
            b += t(48, y, name, 13, TEXT, mono=True)
            b += t(284, y, f"{100*ratio:.1f}%", 12, MUTED, mono=True, extra='text-anchor="end"')
            b += rect(301, y-11, 254, 10, "#183246", 5)
            b += rect(301, y-11, max(2, ratio*254), 10, lang["color"], 5)
        note = "ORIGINAL REPOSITORIES · PROFILE EXCLUDED" if by_repo else "FORKS AND PROFILE ASSETS EXCLUDED"
        b += t(30, 314, note, 10, MUTED, mono=True)
    return svg(588, 340, "Languages used in public repositories", b)


def city(data):
    days = sorted(data["days"], key=lambda d: d["date"])
    b = panel(1200, 438, "THE CITY I BUILD, ONE DAY AT A TIME", "contributions.city")
    b += t(35, 102, "Every contribution leaves a light on.", 25, TEXT, 700)
    b += t(35, 138, str(data["total_contributions"]), 29, MINT, 700, True)
    b += t(115, 138, "contributions · last 12 months", 15, MUTED)
    if days:
        start = date.fromisoformat(days[0]["date"])
        origin = start - timedelta(days=(start.weekday()+1) % 7)
        by_date = {date.fromisoformat(d["date"]): d["contributionCount"] for d in days}
        last = date.fromisoformat(days[-1]["date"])
        n = (last-origin).days//7 + 1
        grid = []
        for week in range(n):
            for weekday in range(7):
                day = origin + timedelta(days=week*7+weekday)
                if day in by_date:
                    grid.append((week, weekday, day, by_date[day]))
        peak = max(by_date.values(), default=0)
        # True calendar alignment: weeks advance right, weekdays advance left.
        for week, weekday, day, count in sorted(grid, key=lambda v: (v[0]+v[1], v[0])):
            x, y = 177+(week-weekday)*17.7, 220+(week+weekday)*2.7
            h = 0 if count == 0 else 12+math.log1p(count)/math.log1p(max(1, peak))*56
            title = f"{day.isoformat()}: {count} contributions"
            b += f'<g><title>{title}</title>'
            if count:
                b += f'<path d="M{x-8},{y-h+3.5}v{h}l8,3.5v{-h}Z" fill="#187c76" stroke="#103e47" stroke-width=".6"/>'
                b += f'<path d="M{x},{y-h+7}v{h}l8,-3.5v{-h}Z" fill="#26bba0" stroke="#103e47" stroke-width=".6"/>'
            b += f'<path d="M{x},{y-h}l8,3.5 -8,3.5 -8,-3.5Z" fill="{MINT if count else "#102b35"}" stroke="{"#92ffe0" if count else "#21424b"}" stroke-width=".7"/>'
            b += '</g>'
        b += t(35, 406, f"{days[0]['date']}  →  {days[-1]['date']}", 11, MUTED, mono=True)
    b += t(1167, 406, "HEIGHT = DAILY CONTRIBUTIONS", 11, MINT, mono=True, extra='text-anchor="end"')
    return svg(1200, 438, "Isometric city built from real daily GitHub contributions", b)


def arcade(data):
    b = panel(588, 340, "CONTRIBUTION ARCADE", "space.loop")
    b += t(29, 80, "SPACE SHOOTER", 17, VIOLET, 700, True)
    b += t(556, 80, "♥ ♥ ♥", 19, "#ff719b", extra='text-anchor="end"')
    for i in range(34):
        x, y = 28+(i*97)%525, 96+(i*37)%209
        b += f'<circle cx="{x}" cy="{y}" r="{1 if i%4 else 1.7}" fill="{MUTED}" opacity=".45"/>'
    b += '<g class="fleet" fill="#54efb5" shape-rendering="crispEdges">'
    for row in range(3):
        for col in range(12):
            x, y = 75+col*37, 104+row*28
            b += f'<path d="M{x+4} {y}h4v4h8v-4h4v8h4v12h-4v-4H{x+4}v4h-4V{y+8}h4z" opacity="{1-row*.18}"/>'
            b += rect(x+4, y+8, 4, 4, "#101b27") + rect(x+16, y+8, 4, 4, "#101b27")
    b += '</g>'
    b += '<g class="shot">' + rect(292, 201, 4, 19, CYAN, 2) + '</g>'
    b += '<g class="float"><path d="M294 237l9 18v12h15v13h-48v-13h15v-12Z" fill="#a5b5ff"/><path d="M290 249h8v22h-8Z" fill="#65d8ff"/><path d="M285 280h18l-9 25Z" fill="#54efb5" opacity=".7"/></g>'
    b += t(29, 318, "CONTRIBUTIONS: " + str(data["total_contributions"]), 10, MINT, mono=True)
    b += t(557, 318, "ANIMATED LOOP", 10, MUTED, mono=True, extra='text-anchor="end"')
    return svg(588, 340, "Decorative animated space shooter with contribution count", b)


def chess():
    b = panel(588, 340, "ONE MOVE AT A TIME", "chess.loop")
    ox, oy, step = 33, 65, 29
    for row in range(8):
        for col in range(8):
            b += rect(ox+col*step, oy+row*step, step, step, "#1d354a" if (row+col)%2 else "#112334")
    # A decorative knight move (b1 → d2), with vector pieces for font independence.
    knight_path = "M2 23h23v4H2Z M5 21l1-6 8-6-5-2-4 5-5-4 9-8 9 2 6 9-2 10Z"
    for x, y in [(33+29, 65+6*29), (33+6*29, 65+29)]:
        b += f'<path d="{knight_path}" transform="translate({x+2},{y+1}) scale(.85)" fill="{MINT}"/>'
    b += f'<g class="knight"><path d="{knight_path}" transform="translate({ox+29+2},{oy+7*29+1}) scale(.85)" fill="{TEXT}"/></g>'
    b += t(298, 108, "Think ahead.", 22, TEXT, 700)
    b += t(298, 140, "Keep building.", 22, TEXT, 700)
    b += t(298, 189, "Curiosity is the", 14, MUTED)
    b += t(298, 213, "best opening move.", 14, MUTED)
    b += t(298, 271, "CYBERSECURITY", 12, MINT, mono=True)
    b += t(298, 293, "ARTIFICIAL INTELLIGENCE", 11, VIOLET, mono=True)
    b += t(29, 320, "A VISUAL LOOP · ALWAYS LEARNING", 10, MUTED, mono=True)
    return svg(588, 340, "Decorative chessboard with an animated knight move", b)


def toolkit(config):
    b = panel(1200, 132, "TOOLS I'M WORKING WITH", "toolkit.list")
    x = 27
    for i, name in enumerate(config["toolkit"]):
        p, width = pill(x, 73, name, [MINT, CYAN, VIOLET][i%3], 16)
        b += p
        x += width+15
    return svg(1200, 132, "Learning toolkit: " + ", ".join(config["toolkit"]), b)


def about(config):
    school, _, exchange = config["education"].partition(" · ")
    interests = config["focus"].split(" · ")
    b = panel(1200, 190, "ABOUT.ME", "whoami --details")
    b += t(30, 82, "$ whoami", 14, MINT, mono=True)
    b += t(30, 114, config["role"] + " · " + school, 22, TEXT, 700)
    b += t(30, 146, exchange or config["education"], 17, TEXT)
    b += t(30, 173, "Learning through Python, web projects and Linux.", 13, MUTED)
    b += rect(740, 72, 1, 96, "#284b60")
    b += t(781, 87, "CURRENT INTERESTS", 11, MUTED, mono=True)
    b += t(781, 121, interests[0].upper(), 18, MINT, 700, True)
    if len(interests) > 1:
        b += t(781, 153, interests[1].upper(), 16, VIOLET, 700, True)
    return svg(1200, 190, config["name"] + " — education and interests", b)


def link_button(label, detail, color):
    b = rect(1, 1, 586, 68, "url(#panel)", 14, color, 'stroke-opacity=".42"')
    b += t(25, 30, label, 15, color, 700, True)
    b += t(25, 51, detail, 11, MUTED, mono=True)
    b += t(554, 45, "↗", 28, color, extra='text-anchor="end"')
    return svg(588, 70, label + " — " + detail, b)


def projects_header(count):
    b = panel(1200, 94, "PROJECTS.LIST", "./projects.sh --all")
    b += t(28, 78, "A few things I've been building", 20, TEXT, 700)
    b += t(1170, 76, str(count) + " FEATURED REPOSITORIES", 11, MINT, mono=True, extra='text-anchor="end"')
    return svg(1200, 94, "Featured GitHub projects", b)


def project_card(project, settings, index):
    language = project.get("language") or "CODE"
    color = {"HTML": "#ffb26b", "CSS": VIOLET, "Python": CYAN}.get(language, MINT)
    b = panel(588, 286, f"PROJECT // {index:02d}", "public.repo")
    b += f'<circle cx="33" cy="78" r="4" fill="{color}"/>'
    b += t(47, 86, settings["label"], 22, TEXT, 700)
    b += t(28, 112, project["name"], 11, MUTED, mono=True)
    lines = textwrap.wrap(project.get("description") or "Explore this repository on GitHub.", width=49)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip(" .") + "…"
    for row, line in enumerate(lines):
        b += t(28, 143+row*20, line, 15, MUTED)
    x = 28
    for label in settings.get("tags", [])[:3]:
        p, width = pill(x, 205, label, color, 11)
        if x+width > 448:
            break
        b += p
        x += width+9
    # This ring measures the primary language's byte share, never project completion.
    share = project.get("primary_share")
    b += '<circle cx="512" cy="129" r="37" fill="none" stroke="#193447" stroke-width="6"/>'
    if share is not None:
        share = max(0, min(100, float(share)))
        circumference = 2*math.pi*37
        b += f'<circle cx="512" cy="129" r="37" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-dasharray="{circumference*share/100:.2f} {circumference:.2f}" transform="rotate(-90 512 129)"/>'
        b += t(512, 135, f"{share:g}%", 18, TEXT, 700, True, 'text-anchor="middle"')
        b += t(512, 188, language.upper() + " SHARE", 9, color, mono=True, extra='text-anchor="middle"')
    else:
        b += t(512, 135, language[:4].upper(), 17, color, 700, True, 'text-anchor="middle"')
        b += t(512, 188, "PRIMARY LANGUAGE", 9, MUTED, mono=True, extra='text-anchor="middle"')
    b += rect(28, 246, 532, 1, "#213f52")
    b += t(28, 269, f"☆ {project.get('stars', 0)} STARS  ·  PUBLIC", 10, MUTED, mono=True)
    updated = project.get("updated_at", "")[:10]
    b += t(560, 269, "UPDATED " + (updated or "—"), 10, MUTED, mono=True, extra='text-anchor="end"')
    return svg(588, 286, settings["label"] + " — " + project.get("description", ""), b)


def heatmap(data):
    days = sorted(data["days"], key=lambda d: d["date"])
    total = data["total_contributions"]
    active = sum(d["contributionCount"] > 0 for d in days)
    peak = max((d["contributionCount"] for d in days), default=0)
    b = panel(1200, 326, "CONTRIBUTIONS.CALENDAR", "activity.heatmap")
    b += t(30, 85, f"{total:,} contributions in the last year", 25, TEXT, 700)
    b += t(1170, 83, "SNAPSHOT " + data["updated_at"][:10], 10, MUTED, mono=True, extra='text-anchor="end"')
    colors = ["#152a38", "#115341", "#17865f", "#28ba82", MINT]
    if days:
        first = date.fromisoformat(days[0]["date"])
        origin = first - timedelta(days=(first.weekday()+1)%7)
        last = date.fromisoformat(days[-1]["date"])
        weeks = (last-origin).days//7 + 1
        step = min(18, 972/max(1, weeks))
        for week in range(weeks):
            day = origin+timedelta(days=week*7)
            if day.day <= 7:
                b += t(145+week*step, 112, day.strftime("%b"), 11, MUTED, mono=True)
        for weekday, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
            b += t(107, 140+weekday*18, label, 10, MUTED, mono=True, extra='text-anchor="end"')
        for day in days:
            when = date.fromisoformat(day["date"])
            week, weekday = divmod((when-origin).days, 7)
            count = day["contributionCount"]
            level = 0 if count == 0 else min(4, max(1, math.ceil(count/max(1, peak)*4)))
            b += f'<g><title>{when.isoformat()}: {count} contributions</title>'
            b += rect(145+week*step, 127+weekday*18, 13, 13, colors[level], 2)
            b += '</g>'
    b += t(30, 296, f"{active} ACTIVE DAYS   ·   BEST DAY: {peak}", 11, MINT, mono=True)
    b += t(938, 296, "LESS", 10, MUTED, mono=True, extra='text-anchor="end"')
    for i, color in enumerate(colors):
        b += rect(950+i*21, 284, 14, 14, color, 2)
    b += t(1066, 296, "MORE", 10, MUTED, mono=True)
    return svg(1200, 326, "Contribution calendar built from real GitHub contribution dates and counts", b)


def footer(config, data):
    b = rect(1, 1, 1198, 62, "url(#panel)", 14, "url(#accent)", 'stroke-opacity=".35"')
    b += t(26, 27, config["name"].upper() + "  /  BUILD. LEARN. REPEAT.", 12, MINT, 600, True)
    b += t(26, 47, "Stats are a saved snapshot · Rings show language share · Animations are decorative", 11, MUTED)
    b += t(1170, 36, "SOURCE + NOTES ↗", 12, CYAN, 600, True, 'text-anchor="end"')
    return svg(1200, 64, "Profile data and maintenance notes", b)


def readme(config, data):
    def img(name, alt, width="100%", link=None):
        element = f'<img src="{escape(name)}" width="{width}" alt="{escape(alt)}" />'
        return f'<a href="{escape(link)}">{element}</a>' if link else element

    login = config["login"]
    sections = [
        '<!-- Generated by generate_profile.py. Edit profile.json and see SETUP.md for updates. -->',
        img("banner.svg", config["name"] + " — Computer Engineering student", link=config["website"]),
        img("about.svg", config["education"] + ". Interests: " + config["focus"]),
        '<p>\n' + img("portfolio-link.svg", "Open my personal portfolio", "49%", config["website"]) + '\n' + img("repositories-link.svg", "Explore my GitHub repositories", "49%", f"https://github.com/{login}?tab=repositories") + '\n</p>',
        '<p>\n' + img("metrics.svg", "GitHub repositories and contribution statistics", "49%") + '\n' + img("languages.svg", "Language stack across my public repositories", "49%") + '\n</p>',
        img("projects-header.svg", "Featured projects"),
    ]
    available = {project["name"] for project in data.get("projects", [])}
    featured = [project for project in config.get("featured_projects", []) if project["name"] in available]
    for i in range(0, len(featured), 2):
        cards = [img("project-" + project["name"].lower() + ".svg", "Open " + project["label"] + " on GitHub", "49%", f"https://github.com/{login}/{project['name']}") for project in featured[i:i+2]]
        sections.append('<p>\n' + '\n'.join(cards) + '\n</p>')
    sections.extend([
        img("heatmap.svg", "Contribution heatmap with real daily GitHub contributions"),
        img("city.svg", "A three-dimensional city built from my contribution calendar"),
        '<p>\n' + img("arcade.svg", "Decorative space shooter animation", "49%") + '\n' + img("chess.svg", "Decorative chessboard animation", "49%") + '\n</p>',
        img("toolkit.svg", "Python, C, JavaScript, PHP, HTML, CSS, SQL, Git and Linux"),
        img("footer.svg", "Snapshot date, data definitions and maintenance notes", link="SETUP.md"),
    ])
    return '\n\n'.join(sections) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Regenerate using the saved public snapshot")
    args = parser.parse_args()
    config = json.loads((ROOT/"profile.json").read_text())
    snapshot_path = ROOT/"public-snapshot.json"
    if args.offline:
        data = json.loads(snapshot_path.read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required for a live sync; use --offline for the saved snapshot")
        data = fetch_public_data(config["login"], token)
    if data["login"].lower() != config["login"].lower():
        raise SystemExit("The snapshot does not belong to the configured account")
    outputs = {
        "banner.svg": banner(config), "metrics.svg": metrics(data),
        "languages.svg": language_stack(data), "city.svg": city(data),
        "arcade.svg": arcade(data), "chess.svg": chess(), "toolkit.svg": toolkit(config),
        "about.svg": about(config), "heatmap.svg": heatmap(data),
        "portfolio-link.svg": link_button("OPEN PORTFOLIO", config["website"].split("//")[-1].rstrip("/"), MINT),
        "repositories-link.svg": link_button("EXPLORE REPOSITORIES", "github.com/" + config["login"], CYAN),
        "footer.svg": footer(config, data),
        "README.md": readme(config, data),
    }
    available = {project["name"]: project for project in data.get("projects", [])}
    featured = [project for project in config.get("featured_projects", []) if project["name"] in available]
    outputs["projects-header.svg"] = projects_header(len(featured))
    for index, settings in enumerate(featured, 1):
        filename = "project-" + settings["name"].lower() + ".svg"
        outputs[filename] = project_card(available[settings["name"]], settings, index)
    # Build all outputs first. API failures leave the last successful visuals intact.
    ASSETS.mkdir(exist_ok=True)
    for name, content in outputs.items():
        (ASSETS/name).write_text(content, encoding="utf-8")
    if not args.offline:
        snapshot_path.parent.mkdir(exist_ok=True)
        snapshot_path.write_text(json.dumps(data, indent=2)+"\n")
    svg_count = sum(name.endswith(".svg") for name in outputs)
    print(f"Built {svg_count} SVGs and README for @{config['login']}; snapshot {data['updated_at']}")


if __name__ == "__main__":
    main()
