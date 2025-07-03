# GitHub-Star-Organiser

A simple CLI tool that connects to your GitHub account, analyses the README of each starred repository with the OpenAI API and organises them into lists.

## Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the organiser:

```bash
python organize_stars.py --create-new
```

Provide your GitHub OAuth app client ID with `--client-id` (or via `GITHUB_CLIENT_ID`) to log in using the browser-based device flow. Without a client ID a personal access token will be requested instead. You will also be prompted for an OpenAI API key. Lists are stored in `lists.json` and `--create-new` allows new categories to be created automatically.

