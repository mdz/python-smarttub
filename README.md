# python-smarttub

This package provides an API for querying and controlling hot tubs using the SmartTub system.

## Installation
```
pip3 install python-smarttub
```

## CLI
```
python3 -m smarttub --help
python3 -m smarttub -u SMARTTUB_EMAIL -p SMARTTUB_PASSWORD info --status
```

## API
```
from smarttub import SmartTub

async with aiohttp.ClientSession() as session:
  st = SmartTub(session)
  await st.login(username, password)
  account = await st.get_account()
  spas = await account.get_spas()
  for spa in spas:
    spa.get_status()
    spa.get_pumps()
    spa.get_lights()
    ...
    # See pydoc3 smarttub.api for complete API
```

See also `smarttub/__main__.py` for example usage

## Troubleshooting

If this module is not working with your device, please run the following
command and include the output with your bug report:

```bash
python3 -m smarttub -u YOUR_SMARTTUB_EMAIL -p YOUR_SMARTTUB_PASSWORD -vv info -a
```

## Contributing
```bash
uv sync --extra dev
uv run pre-commit install
```
