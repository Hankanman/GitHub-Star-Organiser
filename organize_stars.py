import json
import os
import time
from getpass import getpass

import click
from github import Github
import openai
import requests


def device_login(client_id):
    """Perform GitHub device flow login and return an access token."""
    resp = requests.post(
        "https://github.com/login/device/code",
        data={"client_id": client_id, "scope": "repo read:user"},
        headers={"Accept": "application/json"},
    )
    data = resp.json()
    click.echo(f"Open {data['verification_uri']} and enter code {data['user_code']}")
    while True:
        time.sleep(data.get("interval", 5))
        poll = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "device_code": data["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        result = poll.json()
        if "access_token" in result:
            return result["access_token"]
        if result.get("error") != "authorization_pending":
            raise RuntimeError(result.get("error_description", "Login failed"))


@click.command()
@click.option('--token', help='GitHub personal access token', default=lambda: os.environ.get('GITHUB_TOKEN'))
@click.option('--client-id', help='GitHub OAuth app client ID', default=lambda: os.environ.get('GITHUB_CLIENT_ID'))
@click.option('--list-file', default='lists.json', show_default=True, help='Path to JSON file with category lists')
@click.option('--create-new', is_flag=True, help='Allow creating new lists if the model suggests a new category')
def main(token, client_id, list_file, create_new):
    """Organise starred repositories into lists using OpenAI."""
    if not token:
        if client_id:
            try:
                token = device_login(client_id)
            except Exception as exc:
                click.echo(f'Device login failed: {exc}')
        if not token:
            token = getpass('GitHub token: ')
    gh = Github(token)
    try:
        user = gh.get_user()
        stars = list(user.get_starred())
    except Exception as exc:
        click.echo(f'Failed to fetch starred repositories: {exc}')
        return

    if os.path.exists(list_file):
        with open(list_file, 'r') as fh:
            lists = json.load(fh)
    else:
        lists = {}

    openai.api_key = os.environ.get('OPENAI_API_KEY')
    if not openai.api_key:
        openai.api_key = getpass('OpenAI API key: ')

    for repo in stars:
        full_name = repo.full_name
        # skip if already categorised
        if any(full_name in repos for repos in lists.values()):
            continue
        try:
            readme = repo.get_readme().decoded_content.decode('utf-8', errors='ignore')
        except Exception:
            readme = ''
        prompt = (
            'Suggest a one or two word category for this repository based on its README.\n'
            f'Readme:\n{readme[:4000]}'
        )
        try:
            resp = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0
            )
            category = resp.choices[0].message.content.strip().splitlines()[0]
        except Exception as exc:
            click.echo(f'OpenAI request failed for {full_name}: {exc}')
            category = 'Uncategorised'
        if category not in lists:
            if create_new:
                lists[category] = []
            else:
                category = 'Uncategorised'
                lists.setdefault(category, [])
        lists[category].append(full_name)
        click.echo(f'{full_name} -> {category}')

    with open(list_file, 'w') as fh:
        json.dump(lists, fh, indent=2)
    click.echo(f'Lists saved to {list_file}')


if __name__ == '__main__':
    main()
