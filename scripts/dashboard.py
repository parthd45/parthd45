"""
PARTH'S GITHUB WRAPPED DASHBOARD
================================
Generates a single, modern SVG dashboard using real GitHub GraphQL data.

Repository layout:
    README.md
    dashboard.svg                 # generated automatically
    scripts/dashboard.py          # this file
    .github/workflows/dashboard.yml

Required environment variable:
    GH_TOKEN or GITHUB_TOKEN

GitHub Actions should provide:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

Customize the CONFIG section below to change the username, colours,
dashboard title, card labels, and number of repositories displayed.
No third-party Python packages are required.
"""

import html
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


# ============================================================
# CONFIG — EDIT THESE SETTINGS
# ============================================================

CONFIG = {
    "username": "parthd45",
    "dashboard_title": "GITHUB WRAPPED",
    "subtitle": "A YEAR OF BUILDING, LEARNING & CONTRIBUTING",
    "output_file": "dashboard.svg",

    # Canvas size
    "width": 1200,
    "height": 920,

    # Number of public repositories to inspect for stars/languages.
    # GitHub GraphQL returns up to 100 repositories in this script.
    "repository_sample_size": 100,

    # Show this many repositories in the repository panel.
    "top_repositories_to_show": 4,

    # Theme colours
    "background": "#090D18",
    "panel": "#111827",
    "panel_alt": "#151E2E",
    "border": "#263449",
    "text": "#F3F4F6",
    "muted": "#94A3B8",
    "cyan": "#00E5FF",
    "purple": "#A78BFA",
    "green": "#34D399",
    "yellow": "#FBBF24",
    "pink": "#FB7185",

    # Contribution heatmap levels
    "heatmap_colors": [
        "#172033",  # 0 contributions
        "#064E3B",  # 1–2
        "#047857",  # 3–5
        "#10B981",  # 6–9
        "#6EE7B7",  # 10+
    ],
}


# ============================================================
# GITHUB GRAPHQL
# ============================================================

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    login
    avatarUrl
    bio
    followers {
      totalCount
    }
    following {
      totalCount
