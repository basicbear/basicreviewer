## Usage
```sh
# Create a workspace
crev init <workspace folder>

# Pull all repos in `configs.json`
crev pull

# Extract PRs specified in `configs.json`
# requires crev pull
crev extract

# Summarize Repo using configs.json repo name
# requires crev pull
# supports --context-only
crev sum repo <repo name> 

# Summarize Repo using configs.json repo name and pr number
# requires crev extract
# supports --context-only
crev sum pr <repo name> <pr number>


```