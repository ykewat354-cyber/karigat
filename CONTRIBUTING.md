# Contributing

Install a development checkout with `python -m pip install -e .`. Run `python -m unittest discover -s tests -v` without provider credentials. Browser evaluation additionally requires Node and Chromium inside a Termux proot Debian environment.

For a bug, provide a minimal synthetic input, the expected behavior and the observed failure. For a fix, include a regression test and distinguish mocked results from live verification. Please omit credentials, account details, journals, screenshots of private projects and raw provider transcripts from issues and pull requests.
