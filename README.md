# Timor GIS

Timor Leste GIS data as Django models
This initial release uses administrative boundariew from Estrada, tweaked to include Atauro as a separate entity, with pcode which are intended to match existing data from PNDS.

## Environment

This is intended to be compatible with:

- Django 4.1+
- Python 3.10+

```sh
gh repo clone catalpainternational/timor_locations
cd timor_locations
poetry install
```

### Pre Commit

If `pre-commit` is installed your code will be checked before commit.
This includes

- black
- flake8
- isort
- mypy

The same checks are run on push. See `pytest.yaml` for details on the checks being run.

### New Release

For a new release, change the `version` property in pyproject.toml and push a git tag with the version number

See `build.yaml` for details on release tagging

## Changelog

...


## Manually Uploading a new version to PyPi

Bump `pyproject.toml`
Then run `poetry build` and `poetry publish`

```bash
poetry build
poetry publish
```

See the file `build.yml` for the workflow
