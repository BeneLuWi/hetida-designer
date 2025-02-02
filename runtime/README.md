# Hetida Designer Runtime and Backend

The hetida designer runtime is the hetida designer submodule responsible for execution of Python code and workflows.

The hetida designer backend is the submodule which offers the API for frontend and for 3rd party services.

Both are written in Python and their code resides in the runtime subdirectory.

> **Note**: All described command line commands in this file assume that the runtime subdirectory of the hetida designer repository is the current working directory.

## Development Setup
Make sure Python 3.9 is installed and available on your path. You may need additional packages like a C compiler (e.g. gcc) depending on your OS's availability of precompiled packages for numerical libraries like **numpy** or **scipy**. We recommend Linux as operating system for development.

1. Navigate to the `runtime` folder.
2. Create virtual environment: `python3.9 -m venv venv`
3. Activate virtual environment: `source venv/bin/activate`
4. Install dependency management tooling: `python -m pip install pip==21.3.1 pip-tools==6.4.0 wheel==0.37.0`
5. Install development dependencies: `pip-sync ./requirements.txt ./requirements-dev.txt`

Now a development web server using a sqlite in-memory db can be started via
```
python main.py
```

If you want to develop against the postgres db running in the docker-compose dev environment the command is
```
HD_DATABASE_URL="postgresql+psycopg2://hetida_designer_dbuser:hetida_designer_dbpasswd@localhost:5430/hetida_designer_db" python main.py
```

In both cases the OpenAPI UI can be found at http://localhost:8000/docs.

Note that this starts runtime+backend combined. If you only want one of both you have to deactivate the other one by setting one of the environment variables `HD_IS_BACKEND_SERVICE` or `HD_IS_RUNTIME_SERVICE` to `false`.

When deactivating the backend endpoints you do not need to specify a database connection URL.

All following commands assume that that the virtual environment is active (step 3).

## Dependency Management
For the hetida designer runtime/backend we rely on [pip-tools](https://github.com/jazzband/pip-tools) for depedency management.
Pip-tools supports having a tree of interdependant dependency sets such that each set is locked with its locked dependant dependency sets as constraints. This is called ["layered dependencies"](https://github.com/jazzband/pip-tools#workflow-for-layered-requirements) in the pip-tools documentation.

This feature allows users of the runtime to [merge their specific Python dependencies](../docs/custom_python_dependencies.md) in their own docker images.

### Basic pip-tools usage
Abstract dependencies go into `requirements.in` while abstract development-only dependencies (test libraries, code quality check libraries etc) should be placed in `requirements-dev.in`.

All following commands are run with activated development virtual environment.

#### Locking Dependencies
Lock all dependencies via
```
rm requirements.txt requirements-dev.txt && pip-compile --generate-hashes && pip-compile --generate-hashes requirements-dev.in
```
This updates the locked dependency files `requirements.txt` and `requirements-dev.txt`.

#### Updating development virtual environment
Update your development virtual environment to the current locked dependencies via 

```
pip-sync requirements.txt requirements-dev.txt
```

#### Upgrade dependencies
All dependencies are upgraded via
```
pip-compile --generate-hashes --upgrade && pip-compile --generate-hashes --upgrade requirements-dev.in
```

### <a name="runtime-tests"></a> Tests
With activated virtual environment, run
```
python -m pytest --cov=hetdesrun tests
```
from the runtime directory to obtain unit test results including coverage report.

### Code Quality Check
Pylint can be used to check static code quality during development:
```
pylint hetdesrun
```
Used pylint rules are controlled through the `pylintrc` file in the runtime directory of the repository.

It is recommended to set up your editor/IDE to use pylint with this `pylintrc`.

### Code formatting
As code formatter, [black](https://github.com/ambv/black) is used. It is recommended to configure your IDE to automatically format Python code with black during save. Currently black formatting is not enforced as part of the build process.

### Type Hints
Runtime/Backend code is currently mostly type hinted. You may use [mypy](http://mypy-lang.org/) for static type checking via
```
python3 -m mypy hetdesrun
```
The Mypy configuration can be found in `mypy.ini` file in /runtime directory.

We recommend to set up your IDE to use mypy with this mypy configuration file.
