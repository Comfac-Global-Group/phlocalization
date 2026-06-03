"""
Module for automated PR code review using GitHub API and cloud function.
This script fetches PR diffs, filters out .github folder changes, and sends them for review.
"""

import json
import os
import sys

import requests


def filter_diff(diff_text):
    """
    Filter out changes from .github folder in the diff.

    Args:
        diff_text (str): The raw diff text from GitHub API

    Returns:
        str: Filtered diff text without .github folder changes
    """
    lines = diff_text.split('\n')
    filtered_lines = []
    skip_file = False

    for line in lines:
        # Check if this is a new file header
        if line.startswith('diff --git'):
            # Check if the file is in .github folder
            if '/.github/' in line or line.endswith('/.github') or ' b/.github/' in line:
                skip_file = True
            else:
                skip_file = False

        # Include the line if we're not skipping this file
        if not skip_file:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def get_pr_diff(owner, repo, pr_number, github_token):
    """
    Fetch the diff for a specific pull request from GitHub API.

    Args:
        owner (str): Repository owner
        repo (str): Repository name
        pr_number (int): Pull request number
        github_token (str): GitHub authentication token

    Returns:
        str: The diff text from the PR

    Raises:
        SystemExit: If the API request fails
    """
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'
    headers = {'Accept': 'application/vnd.github.v3.diff', 'Authorization': f'token {github_token}'}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print(f'Error: Failed to fetch PR diff (HTTP {response.status_code}).', file=sys.stderr)
        sys.exit(1)
    return response.text


def get_code_review(diff_text, cloud_function_url):
    """
    Send the diff to a cloud function for AI-powered code review.

    Args:
        diff_text (str): The filtered diff text to review
        cloud_function_url (str): URL of the cloud function endpoint

    Returns:
        str: The code review response from the cloud function

    Raises:
        SystemExit: If the cloud function call fails or API key is missing
    """
    function_api_key = os.environ.get('FUNCTION_API_KEY')
    if not function_api_key:
        print('Error: FUNCTION_API_KEY not found', file=sys.stderr)
        sys.exit(1)

    headers = {'Content-Type': 'application/json', 'Authorization': function_api_key}
    payload = json.dumps({'diff': diff_text})

    try:
        response = requests.post(cloud_function_url, headers=headers, data=payload, timeout=60)
        if response.status_code != 200:
            error_msg = (
                f"Error: Cloud Function returned HTTP "
                f"{response.status_code}: {response.text}"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        return response.json().get('review', 'No review received.')
    except requests.exceptions.RequestException as exc:
        print(f'Error calling Cloud Function: {exc}', file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to orchestrate the PR review process.
    Fetches PR data, retrieves diff, filters it, and sends for review.
    """
    github_event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not github_event_path:
        print('Error: GITHUB_EVENT_PATH not set.', file=sys.stderr)
        sys.exit(1)

    with open(github_event_path, encoding='utf-8') as file:
        event_data = json.load(file)

    pull_request = event_data.get('pull_request')
    if not pull_request:
        print('Error: This event is not a pull_request.', file=sys.stderr)
        sys.exit(1)

    pr_number = pull_request.get('number')
    if not pr_number:
        print('Error: Could not determine pull request number.', file=sys.stderr)
        sys.exit(1)

    repo_full = os.environ.get('GITHUB_REPOSITORY')
    if not repo_full or '/' not in repo_full:
        print('Error: GITHUB_REPOSITORY not set or invalid.', file=sys.stderr)
        sys.exit(1)
    owner, repo = repo_full.split('/')

    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print('Error: GITHUB_TOKEN not set.', file=sys.stderr)
        sys.exit(1)

    cloud_function_url = os.environ.get('CLOUD_FUNCTION_URL')
    print(cloud_function_url, file=sys.stderr)
    if not cloud_function_url:
        print('Error: CLOUD_FUNCTION_URL not set.', file=sys.stderr)
        sys.exit(1)

    print(f'Fetching diff for PR #{pr_number} in {owner}/{repo}...', file=sys.stderr)
    diff_text = get_pr_diff(owner, repo, pr_number, github_token)

    if not diff_text:
        print('Error: No diff fetched.', file=sys.stderr)
        sys.exit(1)

    # Filter out .github folder changes
    print('Filtering out .github folder changes...', file=sys.stderr)
    filtered_diff = filter_diff(diff_text)

    if not filtered_diff.strip():
        print('No changes to review after filtering .github folder.', file=sys.stderr)
        print('✅ No code changes to review (only .github folder modifications).')
        sys.exit(0)

    print('Sending diff to Cloud Function for code review...', file=sys.stderr)
    review = get_code_review(filtered_diff, cloud_function_url)
    print(review)


if __name__ == '__main__':
    main()
