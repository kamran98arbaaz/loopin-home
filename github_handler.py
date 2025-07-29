import requests
import base64
import json
from github_config import *

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_file_sha():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    response = requests.get(url, headers=headers)
    return response.json().get("sha")

def load_updates():
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
    response = requests.get(url)
    return response.json()  # Assumes it's valid JSON like a list of updates


def save_updates(new_data):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    sha = get_file_sha()  # Required to overwrite the existing file

    # Convert Python data (dict or list) to JSON string and then encode to base64
    encoded_data = base64.b64encode(
        bytes(json.dumps(new_data, indent=2), 'utf-8')
    ).decode('utf-8')

    commit_msg = "Update from LoopIn app"
    payload = {
        "message": commit_msg,
        "content": encoded_data,
        "sha": sha,
        "branch": BRANCH
    }

    response = requests.put(url, headers=headers, json=payload)
    return response.status_code == 200