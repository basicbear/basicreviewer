# basicreviewer
Open source code review, performance review, and CV tool. Designed to help software engineers market themselves and improve their skills.

# Use
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
- Run all tests: `uv run --with pytest pytest tests/ -v`
- Run just init tests: `uv run --with pytest pytest tests/init/test_base.py -v`



# Shout outs
- To all the people working hard to make the world a better place!

- Initial repo setup: [mathspp.com](https://mathspp.com/blog/using-uv-to-build-and-install-python-cli-apps)
- Testing setup: [pydevtools.com](https://pydevtools.com/handbook/tutorial/setting-up-testing-with-pytest-and-uv/)