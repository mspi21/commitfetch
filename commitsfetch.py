#!/usr/bin/env python
import json
import requests
from datetime import datetime, timedelta
from dotenv import dotenv_values
from sys import argv


def print_usage_and_exit(code):
    print(f'Usage: {argv[0]} <OPTION> ["keywords"] ["labels"] <repository id (AUTHOR/REPO)> <outfile>')
    print('	OPTIONS (mut.ex.):')
    print('		-c: fetch commits')
    print('		-p: fetch pull requests')
    print('		-i: fetch issues')
    print('     keywords - list of keywords to be filtered in title (optional)')
    print('     labels - list of labels to be filtered in labels (optional)')
    exit(code)


def try_parse_args_or_exit() -> tuple[str, str, str, str, list]:
    if len(argv) < 4:
        print_usage_and_exit(1)
    optional_filter = [[], []]
    action = argv[1]
    if (action == '-c'):
        action = 'commits'
    elif (action == '-p'):
        action = 'prs'
    elif (action == '-i'):
        action = 'issues'
    else:
        print_usage_and_exit(1)
    if (len(argv) >= 5):
        optional_filter[0] = argv[2].strip('"').split(' ')
    if (len(argv) == 6):
        optional_filter[1] = argv[3].strip('"').split(' ')

    repo = argv[-2].split('/')
    assert len(repo) == 2

    repo_owner, repo_name = repo
    outfile = argv[-1]

    return repo_owner, repo_name, outfile, action, optional_filter


def find(func, iter):
    for x in iter:
        if func(x):
            return x
    return None


def fetch(url, transform):
    gh_access_token = dotenv_values()["GITHUB_ACCESS_TOKEN"]

    response = requests.get(url,
                            params={'state': 'all', 'per_page': 500},
                            headers={'Authorization': f'Bearer {gh_access_token}'}
                            )

    response.raise_for_status()

    rl_limit = int(response.headers["X-RateLimit-Limit"])
    rl_remaining = int(response.headers["X-RateLimit-Remaining"])
    rl_reset = int(response.headers["X-RateLimit-Reset"])
    tc_now = int(datetime.now().timestamp())

    try:
        links = response.headers["Link"].split(',')
    except:
        links = []

    print(f'[info] Current rate limit: {rl_limit}')
    print(f'[info] Remaining requests: {rl_remaining}')
    print(f'[info] Rate limit will reset in {timedelta(seconds = rl_reset - tc_now)}')

    prs_page = list(map(transform, response.json()))
    next = find(lambda link: 'rel="next"' in link, links)
    last = find(lambda link: 'rel="last"' in link, links)

    if next is not None:
        next = next.split(';')[0].strip('<> ')
        print(f'[info] Advancing to next page {next}')

        if last is not None:
            last = last.split(';')[0].strip('<> ')
            print(f'[info] Last page is {last}')

    return prs_page, next


def fetch_paged(fn, url, transform, op_filter):
    result_page, next = fn(url, transform)
    results = [] + result_page

    while next is not None:
        result_page, next = fn(next, transform)
        results = results + result_page

    if len(op_filter[0]) > 0 or len(op_filter[1]) > 0:
        keywords = op_filter[0]
        filter_labels = op_filter[1]
        filtered = []
        for item in results:
            title = item.get('title')

            label_names = [label.get('name') for label in item.get('labels', {})]

            if ((any(keyword in title for keyword in keywords) and keywords != [''])
                    or any(label in label_names for label in filter_labels)):
                filtered.append(item)
        return filtered
    else:
        return results




if __name__ == '__main__':
    repo_owner, repo_name, outfile, action, optional_filter = try_parse_args_or_exit()
    transform_pr = lambda pullreq: {
        'url': pullreq.get('url'),
        'id': pullreq.get('id'),
        'number': pullreq.get('number'),
        'state': pullreq.get('state'),
        'title': pullreq.get('title'),
        'body': pullreq.get('body'),
        'created_at': pullreq.get('created_at'),
        'updated_at': pullreq.get('updated_at'),
        'closed_at': pullreq.get('closed_at'),
        'merged_at': pullreq.get('merged_at'),
        'user_login': pullreq['user'].get('login'),
        'user_email': pullreq['user'].get('email'),
        'user_type': pullreq['user'].get('type'),
        'merge_commit_sha': pullreq.get('merge_commit_sha'),
        'author_association': pullreq.get('author_association'),
        'labels': [x['name'] for x in pullreq['labels']],
    }

    transform_commit = lambda commit: {
        'sha': commit['sha'],
        'author_name': commit['commit']['author']['name'],
        'author_email': commit['commit']['author']['email'],
        'author_date': commit['commit']['author']['date'],
        'committer_name': commit['commit']['committer']['name'],
        'committer_email': commit['commit']['committer']['email'],
        'committer_date': commit['commit']['committer']['date'],
        'title': commit['commit']['message']
    }

    transform_issue = lambda issue: {
        'url': issue['url'],
        'title': issue['title'],
        'state': issue['state'],
        'body': issue['body'],
        'created_at': issue['created_at'],
        'labels': issue['labels'],
    }

    if action == 'commits':
        result = fetch_paged(fetch, f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits', transform_commit,
                             optional_filter)
    elif action == 'prs':
        result = fetch_paged(fetch, f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls', transform_pr,
                             optional_filter)
    elif action == 'issues':
        result = fetch_paged(fetch, f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues', transform_issue,
                             optional_filter)
    else:
        raise AssertionError("Illegal config")

    if input(f'Done. Save output to "{outfile}"? [y/*] ').lower().strip() == 'y':
        with open(outfile, 'w') as f:
            f.write(json.dumps(result))
    else:
        print(json.dumps(result))
