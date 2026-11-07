
import os
import json
import urllib.request
import html
from datetime import date, timedelta

USERNAME = "parthd45"
TOKEN = os.environ["GH_TOKEN"]
YEAR = date.today().year

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    followers { totalCount }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
    ) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 10, orderBy: SIZE) {
          edges {
            size
            node { name }
          }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}
"""

def github_data():
    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME}
    }).encode()

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())

    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))

    return result["data"]["user"]


def safe(value):
    return html.escape(str(value))


def streaks(days):
    best = 0
    current = 0
    run = 0

    for item in days:
        if item["contributionCount"] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0

    today = date.today()
    valid = [
        item for item in days
        if date.fromisoformat(item["date"]) <= today
    ]

    if valid:
        latest = date.fromisoformat(valid[-1]["date"])
        if latest >= today - timedelta(days=1):
            for item in reversed(valid):
                if item["contributionCount"] > 0:
                    current += 1
                else:
                    break

    return current, best


def generate_svg(user):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    contribution_days = [
        day
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]

    current_streak, longest_streak = streaks(contribution_days)

    repos = user["repositories"]["nodes"]
    stars = sum(repo["stargazerCount"] for repo in repos)
    forks = sum(repo["forkCount"] for repo in repos)

    languages = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            languages[name] = languages.get(name, 0) + edge["size"]

    top_languages = sorted(
        languages.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    total_bytes = sum(value for _, value in top_languages) or 1

    width = 1200
    height = 760

    parts = []

    def add(value):
        parts.append(value)

    def text(x, y, value, size=18, color="#E6EDF3",
             weight="normal"):
        add(
            f'<text x="{x}" y="{y}" fill="{color}" '
            f'font-size="{size}" font-weight="{weight}" '
            f'font-family="Arial, sans-serif">{safe(value)}</text>'
        )

    def card(x, y, w, h, title, value, accent):
        add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="16" fill="#111827" stroke="#263449"/>'
        )
        add(
            f'<rect x="{x}" y="{y}" width="5" height="{h}" '
            f'rx="3" fill="{accent}"/>'
        )
        text(x + 20, y + 32, title, 14, "#9CA3AF")
        text(x + 20, y + 76, value, 30, accent, "bold")

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    add("""
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#101827"/>
        <stop offset="100%" stop-color="#090D18"/>
      </linearGradient>
      <linearGradient id="title" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#00E5FF"/>
        <stop offset="100%" stop-color="#A78BFA"/>
      </linearGradient>
    </defs>
    """)

    add('<rect width="1200" height="760" rx="24" fill="url(#bg)"/>')
    add('<rect x="1" y="1" width="1198" height="758" rx="24" fill="none" stroke="#263449"/>')

    text(40, 58, "GITHUB WRAPPED", 17, "#00E5FF", "bold")
    text(40, 105, user["name"] or USERNAME, 34, "#FFFFFF", "bold")
    text(40, 138, f"@{USERNAME}  |  {YEAR} YEAR IN CODE", 15, "#9CA3AF")

    text(40, 190, "CONTRIBUTION ACTIVITY", 16, "#E6EDF3", "bold")

    # Contribution heatmap
    day_index = 0
    cell = 13
    gap = 5
    start_x = 40
    start_y = 210

    for week in calendar["weeks"][-53:]:
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            color = (
                "#0D3327" if count == 0 else
                "#006D4A" if count < 3 else
                "#00A86B" if count < 6 else
                "#00D68F"
            )
            x = start_x + day_index * (cell + gap)
            y = start_y + (
                date.fromisoformat(day["date"]).weekday()
                * (cell + gap)
            )
            add(
                f'<rect x="{x}" y="{y}" width="{cell}" '
                f'height="{cell}" rx="3" fill="{color}">'
                f'<title>{safe(day["date"])}: {count} contributions</title>'
                f'</rect>'
            )

        day_index += 1

    text(
        40, 355,
        f'{calendar["totalContributions"]:,} contributions in {YEAR}',
        14, "#9CA3AF"
    )

    # Main statistics
    card(40, 390, 260, 115, "TOTAL CONTRIBUTIONS",
         f'{calendar["totalContributions"]:,}', "#00E5FF")

    card(320, 390, 260, 115, "CURRENT STREAK",
         f'{current_streak} DAYS', "#A78BFA")

    card(600, 390, 260, 115, "LONGEST STREAK",
         f'{longest_streak} DAYS', "#FBBF24")

    card(880, 390, 280, 115, "TOTAL STARS",
         str(stars), "#34D399")

    card(40, 525, 260, 115, "PUBLIC REPOSITORIES",
         str(user["repositories"]["totalCount"]), "#A78BFA")

    card(320, 525, 260, 115, "FOLLOWERS",
         str(user["followers"]["totalCount"]), "#00E5FF")

    card(600, 525, 260, 115, "COMMITS",
         str(user["contributionsCollection"]["totalCommitContributions"]),
         "#34D399")

    card(880, 525, 280, 115, "PULL REQUESTS",
         str(user["contributionsCollection"]["totalPullRequestContributions"]),
         "#FBBF24")

    # Languages
    text(40, 695, "TOP LANGUAGES", 15, "#E6EDF3", "bold")

    x = 220
    for name, amount in top_languages:
        percent = amount / total_bytes * 100
        text(x, 695, f"{name} {percent:.1f}%", 13, "#00E5FF")
        x += 190

    text(40, 735, f"Generated automatically from GitHub API | @{USERNAME}",
         12, "#64748B")

    add("</svg>")

    with open("dashboard.svg", "w", encoding="utf-8") as file:
        file.write("".join(parts))


if __name__ == "__main__":
    account = github_data()
    generate_svg(account)
    print("GitHub dashboard generated successfully!")
