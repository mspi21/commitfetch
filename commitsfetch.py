#!/usr/bin/env python
import json
import requests
from datetime import datetime, timedelta
from dotenv import dotenv_values
from sys import argv

def print_usage_and_exit(code):
	print(f'Usage: {argv[0]} <repository id (AUTHOR/REPO)> <outfile>')
	exit(code)

def try_parse_args_or_exit() -> tuple[str, str, str]:
	if len(argv) < 3:
		print_usage_and_exit(1)
	
	repo = argv[1].split('/')
	assert len(repo) == 2

	repo_owner, repo_name = repo
	outfile = argv[2]
	
	return repo_owner, repo_name, outfile

def find(func, iter):
	for x in iter:
		if func(x):
			return x
	return None

def fetch_commits_params(url):
	gh_access_token = dotenv_values()["GITHUB_ACCESS_TOKEN"]

	transform = lambda commit: {
		'sha': commit['sha'],
		'author_name': commit['commit']['author']['name'],
		'author_email': commit['commit']['author']['email'],
		'author_date': commit['commit']['author']['date'],
		'committer_name': commit['commit']['committer']['name'],
		'committer_email': commit['commit']['committer']['email'],
		'committer_date': commit['commit']['committer']['date'],
	}

	response = requests.get(url,
		params={
			'per_page': 500,
		},
		headers={
			'Authorization': f'Bearer {gh_access_token}',
		}
	)

	rl_limit = int(response.headers["X-RateLimit-Limit"])
	rl_remaining = int(response.headers["X-RateLimit-Remaining"])
	rl_reset = int(response.headers["X-RateLimit-Reset"])
	tc_now = int(datetime.now().timestamp())
	
	links = response.headers["Link"].split(',')
		
	print(f'[info] Current rate limit: {rl_limit}')
	print(f'[info] Remaining requests: {rl_remaining}')
	print(f'[info] Rate limit will reset in {timedelta(seconds = rl_reset - tc_now)}')

	commits_page = list(map(transform, response.json()))
	next = find(lambda link: 'rel="next"' in link, links)
	last = find(lambda link: 'rel="last"' in link, links)

	if next is not None:
		next = next.split(';')[0].strip('<> ')
		print(f'[info] Advancing to next page {next}')

		if last is not None:
			last = last.split(';')[0].strip('<> ')
			print(f'[info] Last page is {last}')

	return commits_page, next

def fetch_commits(repo_owner, repo_name):
	commits_page, next = fetch_commits_params(f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits?per_page=500')
	commits = [] + commits_page

	while next is not None:
		commits_page, next = fetch_commits_params(next)
		commits = commits + commits_page

	return commits

if __name__ == '__main__':
	repo_owner, repo_name, outfile = try_parse_args_or_exit()

	commits = fetch_commits(repo_owner, repo_name)
	
	if(input(f'Done. Save output to "{outfile}"? [y/*] ').lower().strip() == 'y'):
		with open(outfile, 'w') as f:
			f.write(json.dumps(commits))
	else:
		print(json.dumps(commits))
