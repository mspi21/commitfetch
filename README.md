# commitfetch

get metadata for all commits / pull requests in a GitHub repository

### Prerequisites
- python 3 + venv module (`python3.11-venv` on Ubuntu 23)
- github personal access token

### Usage
```sh
# Create a virtual python environment & install dependencies
python -m venv .pyenv
.pyenv/bin/pip install python-dotenv
.pyenv/bin/pip install requests

# Create a .env file with your GH token
echo "GITHUB_ACCESS_TOKEN=<insert_your_token_here>" >> .env

# Run the thing (this will print the usage)
.pyenv/bin/python commitsfetch.py

# For example:
.pyenv/bin/python commitsfetch.py -c gpg/libgcrypt commits_libgcrypt.json
.pyenv/bin/python commitsfetch.py -p pyca/cryptography pulls_cryptography.json
```
