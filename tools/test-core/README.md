# Vendored test-core tools

Copied unchanged from [test-core](https://github.com/KakkoiDev/test-core) at commit
`9906fb6b1c5a2bce138d6293b70afb60fe91fb1f` (branch `feat/recipes`), MIT licence (`LICENSE` here). Standard library
only; nothing is installed or downloaded.

| Tool | What it checks here |
|---|---|
| `scenarios.py` | Every scenario in `SCENARIOS.md` has an end-to-end test named after its title, and (with `--junit`) it ran and passed |
| `e2e_coverage.py` | Every control on the e2e pages (`tests/e2e/pages/`, built from `jp_core.web`) is used by a Playwright step; no step uses a control that is gone |
| `flaky_lint.py` | No fixed sleeps, timers used as waits, `.only`, `networkidle` or real hosts in the tests |

```sh
uv run pytest --junitxml=.test-output/pytest-junit.xml
node --test --test-reporter=spec --test-reporter-destination=stdout \
  --test-reporter=junit --test-reporter-destination=.test-output/node-junit.xml browser/test/*.test.js
npm ci --prefix tests/e2e --ignore-scripts && tests/e2e/node_modules/.bin/playwright install chromium
NODE_PATH="$PWD/tests/e2e/node_modules" node --test --test-reporter=spec --test-reporter-destination=stdout \
  --test-reporter=junit --test-reporter-destination=.test-output/e2e-junit.xml tests/e2e/furigana.e2e.mjs
python3 tools/test-core/scenarios.py check SCENARIOS.md \
  --tests tests/test_scenarios.py browser/test/scenarios.test.js tests/e2e/furigana.e2e.mjs \
  --junit .test-output/pytest-junit.xml .test-output/node-junit.xml .test-output/e2e-junit.xml
python3 tools/test-core/e2e_coverage.py --pages tests/e2e/pages/*.html --tests tests/e2e/furigana.e2e.mjs
python3 tools/test-core/flaky_lint.py tests browser/test tests/e2e/furigana.e2e.mjs
```

Every Chromium launch passes `--use-mock-keychain --password-store=basic` (without them headless Chromium on macOS
asks for a keychain).

To update: copy `tools/scenarios.py`, `tools/e2e_coverage.py` and `tools/flaky_lint.py` from a newer test-core
commit unchanged and change the commit above.
