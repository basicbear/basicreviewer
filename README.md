# basicreviewer
Open source code review, performance review, and CV tool. Designed to help software engineers market themselves and improve their skills.



# Use
## Pre-Requisites
- git CLI

## Install
```bash
uv tool install . -e
```

## Uninstall
```bash
uv tool remove crev
```

# Development
## Testing
- Run all tests: `uv run pytest -v`
- Run just init tests: `uv run pytest ./tests/init -v`
- pull tests: `uv run pytest ./tests/pull -v`

#### Unreviewed Tests
- cmd: pull - all except base
- cmd: extract - all
- cmd: sum - all

# Shout outs
- To all the people working hard to make the world a better place!

- Initial repo setup: [mathspp.com](https://mathspp.com/blog/using-uv-to-build-and-install-python-cli-apps)
- Testing setup: [pydevtools.com](https://pydevtools.com/handbook/tutorial/setting-up-testing-with-pytest-and-uv/)