# Diamond Admin Backend

[![codecov](https://codecov.io/github/Diamond-Proj/diamond-admin-backend/graph/badge.svg?token=9RNM7KHVNG)](https://codecov.io/github/Diamond-Proj/diamond-admin-backend)

## Overview

Diamond Admin Backend is an admin Flask server integrating SQLite for database management and Globus Auth for authentication.

## Installation Instructions

### Prerequisites

- Python 3.11
- [uv](https://docs.astral.sh/uv/)

### Setting Up the Project

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Diamond-Proj/diamond-admin-backend.git
   cd diamond-admin-backend
   ```

2. **Set up Python environment:**

   - Install uv if not already installed:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - Install dependencies (uv automatically manages the virtual environment):
     ```bash
     uv sync --dev
     ```
   - Install pre-commit hooks:
     ```bash
     uv run pre-commit install
     ```

3. **Environment Configuration:**

   - Copy the `.env.example` file to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Update the `.env` file with your configuration:
     - Set `SECRET_KEY` for session management
     - Configure Globus Auth credentials (`PORTAL_CLIENT_ID`, `PORTAL_CLIENT_SECRET`)
     - Adjust database path if needed
     - Modify host/port settings if required

4. **Running the Application:**

   - **Development Mode** (with auto-reload):

     ```bash
     uv run flask --app diamond_backend.run:app --debug
     ```

     This uses Flask's built-in server with debug mode enabled.

   - **Production Mode** (using Gunicorn):
     ```bash
     uv run gunicorn diamond_backend.wsgi:app
     ```
     Gunicorn settings are configured via `GUNICORN_CMD_ARGS` in `.env`

5. **Access the Application:**
   - Development: `http://localhost:5328`
   - The port can be configured via `FLASK_RUN_PORT` in `.env`

## Development Commands

```bash
# Run tests
uv run tox -e py311

# Run linting
uv run tox -e lint

# Run type checking
uv run tox -e type

# Format code
uv run tox -e format

# Run all checks
uv run tox
```

## Dependency Management

```bash
# Add production dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Remove dependency
uv remove package-name
```

## Environment Variables

Key environment variables in `.env`:

- `HOST`: Backend service URL (e.g., 'http://localhost:5328')
- `FLASK_RUN_HOST`: Flask development server host
- `FLASK_RUN_PORT`: Flask development server port
- `GUNICORN_CMD_ARGS`: Gunicorn server configuration
  - workers: Number of worker processes
  - threads: Number of threads per worker
  - worker-class: Type of worker process
  - bind: Host and port binding

## Additional Information

- The application uses SQLite for data storage (configured via `DATABASE` in `.env`)
- Authentication is handled through Globus Auth
- CORS is enabled and configured based on the `HOST` environment variable
- Dependencies are managed via `pyproject.toml` with uv
- Development dependencies are defined in the `[dependency-groups]` section
- For production deployment, consider adjusting Gunicorn settings based on your server's capabilities

<br>

Copyright (c) 2024 University of Illinois and others. All rights reserved.

This program and the accompanying materials are made available under the
terms of the Mozilla Public License v2.0 which accompanies this distribution,
and is available at https://www.mozilla.org/en-US/MPL/2.0/
