# Contributing to Yuktara UI

## Development setup

```bash
python -m pip install -e .
python -m novaui setup
python -m pip install -r requirements-dev.txt
```

## Checks before a change

```bash
python -m pytest -q tests/native
python -m compileall -q novaui
```

## Engineering constraints

- Keep the framework native-rendered; do not add HTML, CSS, JavaScript, DOM or WebView dependencies.
- Keep platform APIs behind injectable adapters where practical.
- Add backend-independent unit tests for behavior.
- Clearly distinguish mocked tests from actual OS/runtime validation.
- Preserve the temporary `novaui` Python import namespace until an explicit compatibility migration is planned.
