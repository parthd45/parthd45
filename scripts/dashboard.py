
import os
import json
import html
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

# ============================================================
# GITHUB PROFILE DASHBOARD
# Username: parthd45
# Output: assets/dashboard.svg
# ============================================================

USERNAME = "parthd45"
OUTPUT_FILE = Path("assets/dashboard.svg")

# Dashboard colours
BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GREEN = "#39d353"
BLUE = "#58a6ff"
PURPLE = "#bc8cff"
ORANGE = "#f0883e"

WIDTH = 1100
HEIGHT = 850


# ============================================================
# GITHUB GRAPHQL QUERY
# ============================================================

QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    name
    login
    bio
    avatarUrl
    followers {
      totalCount
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        description
        stargazerCount
        forkCount
        isFork
        url
        primaryLanguage {
          name
          color
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


# ============================================================
# GITHUB API
# ============================================================

def get_github_data():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GitHub token not found. Set GH_TOKEN or GITHUB_TOKEN."
        )

    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=1)
    start_date = today - timedelta(days=364)

    variables = {
        "username": USERNAME,
        "from": start_date.isoformat() + "T00:00:00Z",
        "to": end_date.isoformat() + "T00:00:00Z"
    }

    payload = {
        "query": QUERY,
        "variables": variables
    }

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Profile-Dashboard"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API error {error.code}: {details}"
        ) from error

    if result.get("errors"):
        raise RuntimeError(
            "GitHub GraphQL error: " + json.dumps(result["errors"])
        )

    user = result.get("data", {}).get("user")

    if not user:
        raise RuntimeError(
            f"GitHub user '{USERNAME}' was not found."
        )

    return user


# ============================================================
# SVG HELPERS
# ============================================================

def escape(value):
    return html.escape(str(value or ""), quote=True)


def rect(x, y, width, height, fill=CARD, radius=14,
         stroke=BORDER):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" '
        f'height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" />'
    )


def text(x, y, value, size=14, color=TEXT,
         weight="normal"):
    return (
        f'<text x="{x}" y="{y}" fill="{color}" '
        f'font-size="{size}" font-weight="{weight}" '
        f'font-family="Arial, Helvetica, sans-serif">'
        f'{escape(value)}</text>'
    )


def line(x1, y1, x2, y2, color=BORDER):
    return (
        f'<line x1="{x1}" y1="{y1}" '
        f'x2="{x2}" y2="{y2}" stroke="{color}" />'
    )


def shorten(value, length=55):
    value = str(value or "")
    if len(value) > length:
        return value[:length - 3] + "..."
    return value


# ============================================================
# CONTRIBUTION HEATMAP
# ============================================================

def contribution_color(count):
    if count == 0:
        return "#21262d"
    if count <= 2:
        return "#0e4429"
    if count <= 5:
        return "#006d32"
    if count <= 9:
        return "#26a641"
    return "#39d353"


def draw_heatmap(user):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]

    output = []

    start_x = 65
    start_y = 300
    cell = 12
    gap = 4

    output.append(text(55, 270, "CONTRIBUTION ACTIVITY", 17, TEXT, "bold"))
    output.append(
        text(
            55, 290,
            f'{calendar["totalContributions"]:,} contributions in the last year',
            12, MUTED
        )
    )

    # Day labels
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for index, day in enumerate(day_names):
        if index in [0, 2, 4, 6]:
            output.append(
                text(25, start_y + index * (cell + gap) + 10,
                     day, 9, MUTED)
            )

    # Contribution squares
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date_value = datetime.strptime(
                day["date"], "%Y-%m-%d"
            ).date()

            weekday = date_value.weekday()

            x = start_x + week_index * (cell + gap)
            y = start_y + weekday * (cell + gap)

            color = contribution_color(day["contributionCount"])

            output.append(
                f'<rect x="{x}" y="{y}" width="{cell}" '
                f'height="{cell}" rx="3" fill="{color}">'
                f'<title>{day["date"]}: '
                f'{day["contributionCount"]} contributions</title>'
                f'</rect>'
            )

    # Legend
    legend_x = 790
    legend_y = 430

    output.append(text(legend_x - 45, legend_y + 10, "Less", 10, MUTED))

    for index, color in enumerate([
        "#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"
    ]):
        output.append(
            f'<rect x="{legend_x + index * 20}" y="{legend_y}" '
            f'width="12" height="12" rx="3" fill="{color}" />'
        )

    output.append(text(legend_x + 110, legend_y + 10, "More", 10, MUTED))

    return "\n".join(output)


# ============================================================
# STATISTICS CARDS
# ============================================================

def draw_stat_card(x, y, title, value, accent):
    output = [
        rect(x, y, 235, 100),
        text(x + 20, y + 30, title.upper(), 12, MUTED, "bold"),
        text(x + 20, y + 72, value, 29, accent, "bold")
    ]

    return "\n".join(output)


# ============================================================
# LANGUAGE STATISTICS
# ============================================================

def draw_languages(repositories):
    language_counts = Counter()

    for repo in repositories:
        language = repo.get("primaryLanguage")

        if language and language.get("name"):
            language_counts[language["name"]] += 1

    output = []

    output.append(text(55, 525, "TOP LANGUAGES", 17, TEXT, "bold"))

    if not language_counts:
        output.append(text(55, 560, "No language data available yet.", 13, MUTED))
        return "\n".join(output)

    total = sum(language_counts.values())
    x = 55
    y = 550
    bar_width = 460
    bar_height = 12

    colors = [
        BLUE, PURPLE, GREEN, ORANGE,
        "#f778ba", "#79c0ff", "#d2a8ff"
    ]

    current_x = x

    for index, (language, count) in enumerate(language_counts.most_common(7)):
        percentage = count / total
        segment_width = bar_width * percentage
        color = colors[index % len(colors)]

        output.append(
            f'<rect x="{current_x}" y="{y}" '
            f'width="{segment_width:.2f}" height="{bar_height}" '
            f'rx="3" fill="{color}" />'
        )

        current_x += segment_width

    legend_y = 590

    for index, (language, count) in enumerate(language_counts.most_common(7)):
        column = index % 2
        row = index // 2

        item_x = 55 + column * 240
        item_y = legend_y + row * 28
        color = colors[index % len(colors)]

        output.append(
            f'<circle cx="{item_x + 5}" cy="{item_y - 4}" '
            f'r="5" fill="{color}" />'
        )

        percentage = (count / total) * 100

        output.append(
            text(
                item_x + 18, item_y,
                f"{language}  {percentage:.1f}%",
                12, TEXT
            )
        )

    return "\n".join(output)


# ============================================================
# REPOSITORY HIGHLIGHTS
# ============================================================

def draw_repositories(repositories):
    output = []

    output.append(text(600, 525, "RECENT REPOSITORIES", 17, TEXT, "bold"))

    if not repositories:
        output.append(text(600, 560, "No public repositories found.", 13, MUTED))
        return "\n".join(output)

    # Show up to four recently updated repositories
    visible_repos = repositories[:4]

    for index, repo in enumerate(visible_repos):
        y = 555 + index * 65

        output.append(
            rect(600, y - 22, 445, 56, fill="#111820", radius=9)
        )

        output.append(
            text(617, y, shorten(repo["name"], 35), 13, BLUE, "bold")
        )

        description = shorten(
            repo.get("description") or "No description provided",
            58
        )

        output.append(
            text(617, y + 18, description, 10, MUTED)
        )

        language = repo.get("primaryLanguage")
        language_name = language["name"] if language else "Other"

        details = (
            f'{language_name}  |  '
            f'★ {repo["stargazerCount"]}  |  '
            f'Forks {repo["forkCount"]}'
        )

        output.append(
            text(617, y + 34, details, 10, TEXT)
        )

    return "\n".join(output)


# ============================================================
# BUILD DASHBOARD
# ============================================================

def create_dashboard(user):
    repositories = user["repositories"]["nodes"]

    total_repos = user["repositories"]["totalCount"]
    followers = user["followers"]["totalCount"]

    total_stars = sum(
        repo["stargazerCount"] for repo in repositories
    )

    total_forks = sum(
        repo["forkCount"] for repo in repositories
    )

    display_name = user.get("name") or user["login"]
    bio = user.get("bio") or "Developer | Data Analytics | Python"

    output = []

    output.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">'
    )

    output.append(
        f'<rect width="{WIDTH}" height="{HEIGHT}" '
        f'rx="20" fill="{BG}" />'
    )

    # Header
    output.append(text(55, 65, "GITHUB WRAPPED", 15, GREEN, "bold"))
    output.append(text(55, 110, display_name, 34, TEXT, "bold"))
    output.append(text(55, 140, f"@{USERNAME}", 15, MUTED))
    output.append(text(55, 170, shorten(bio, 100), 13, MUTED))

    output.append(
        text(
            1045, 65,
            datetime.now().strftime("%b %Y").upper(),
            12, MUTED
        )
    )

    output.append(line(55, 195, 1045, 195))

    # Statistics
    output.append(
        draw_stat_card(55, 215, "Public Repositories",
                       str(total_repos), BLUE)
    )

    output.append(
        draw_stat_card(310, 215, "Total Stars",
                       str(total_stars), GREEN)
    )

    output.append(
        draw_stat_card(565, 215, "Followers",
                       str(followers), PURPLE)
    )

    output.append(
        draw_stat_card(820, 215, "Total Forks",
                       str(total_forks), ORANGE)
    )

    # Contribution heatmap
    output.append(draw_heatmap(user))

    # Bottom sections
    output.append(draw_languages(repositories))
    output.append(draw_repositories(repositories))

    # Footer
    output.append(line(55, 810, 1045, 810))

    output.append(
        text(
            55, 835,
            "Generated automatically with GitHub Actions",
            11, MUTED
        )
    )

    output.append(
        text(
            1045, 835,
            "github.com/parthd45",
            11, BLUE
        )
    )

    output.append("</svg>")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(output), encoding="utf-8")

    print(f"Dashboard successfully generated: {OUTPUT_FILE}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("Fetching GitHub profile data...")

    user = get_github_data()

    print("Generating dashboard...")

    create_dashboard(user)

    print("Done!")


if __name__ == "__main__":
    main()
