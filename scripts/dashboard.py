    x, y, w, h = 620, 650, 540, 220
    svg.rect(x, y, w, h, c["panel"], 18, c["border"])
    svg.text(x + 22, y + 32, "REPOSITORY HIGHLIGHTS", 14, c["text"], "bold")

    top_repos = sorted(
        repositories,
        key=lambda repo: (
            int(repo.get("stargazerCount", 0)),
            int(repo.get("forkCount", 0))
        ),
        reverse=True
    )[:CONFIG["top_repositories_to_show"]]

    if not top_repos:
        svg.text(x + 22, y + 85, "No public repositories found.", 13, c["muted"])
        return

    for index, repo in enumerate(top_repos):
        row_y = y + 76 + index * 34
        name = repo.get("name", "Repository")
        language = (repo.get("primaryLanguage") or {}).get("name", "N/A")
        stars = int(repo.get("stargazerCount", 0))
        forks = int(repo.get("forkCount", 0))

        svg.text(x + 22, row_y, name[:30], 13, c["cyan"], "bold")
        svg.text(x + 22, row_y + 16, language, 10, c["muted"])
        svg.text(
            x + w - 22, row_y + 2,
            f"★ {stars}    Forks {forks}",
            11, c["yellow"], anchor="end"
        )


def render_dashboard(user, year, today):
    c = CONFIG
    width, height = c["width"], c["height"]
    svg = SVG(width, height)

    svg.add(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="GitHub Wrapped dashboard for {html.escape(user["login"])}">'
    )
    add_defs(svg)
    svg.add(
        f'<rect width="{width}" height="{height}" rx="24" '
        f'fill="url(#backgroundGradient)"/>'
    )
    svg.add(
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" '
        f'rx="24" fill="none" stroke="{c["border"]}"/>'
    )

    days = get_contribution_days(user)
    repositories = user["repositories"]["nodes"]

    draw_header(svg, user, year)
    draw_heatmap(svg, days)
    draw_stats(svg, user, days, today)
    draw_languages(svg, repositories)
    draw_repositories(svg, repositories)

    svg.text(
        40, 900,
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  •  "
        f"Source: GitHub GraphQL API  •  @{user['login']}",
        11, c["muted"]
    )

    svg.add("</svg>")
    return svg.finish()


# ============================================================
# MAIN
# ============================================================

def main():
    username = CONFIG["username"]
    output_path = Path(CONFIG["output_file"])

    print(f"Fetching GitHub data for @{username}...")
    user, year = fetch_github_profile(username)

    print("Preparing contribution and repository statistics...")
    svg_content = render_dashboard(user, year, date.today())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")

    print(f"Dashboard generated: {output_path.resolve()}")
    print(f"Repositories returned: {len(user['repositories']['nodes'])}")
    print(
        "Contributions this year: "
        f"{user['contributionsCollection']['contributionCalendar']['totalContributions']}"
    )
    print("Done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
