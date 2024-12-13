# Diamond Admin Backend

## Overview

Diamond Admin Backend is an admin Flask server integrating SQLite for database management and Globus Auth for authentication.

## Installation Instructions

### Prerequisites

- Python 3.x
- pip (Python package installer)
- virtualenv or venv (recommended for isolated environments)

### Setting Up the Project

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Diamond-Proj/diamond-admin-backend.git
   cd diamond-admin-backend
   ```

2. **Set up Python environment:**

   - Create a virtual environment:
     ```bash
     python -m venv venv
     ```
   - Activate the virtual environment:
     ```bash
     # For Windows
     .\venv\Scripts\activate
     # For Unix or MacOS
     source venv/bin/activate
     ```
   - Install Python dependencies:
     ```bash
     pip install -r requirements.txt
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
     flask --app run:app run
     ```

     This uses Flask's built-in server with debug mode enabled.

   - **Production Mode** (using Gunicorn):
     ```bash
     gunicorn wsgi:app
     ```
     Gunicorn settings are configured via `GUNICORN_CMD_ARGS` in `.env`

5. **Access the Application:**
   - Development: `http://localhost:5328`
   - The port can be configured via `FLASK_RUN_PORT` in `.env`

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
- For production deployment, consider adjusting Gunicorn settings based on your server's capabilities

<br>

Copyright (c) 2024 University of Illinois and others. All rights reserved.

This program and the accompanying materials are made available under the
terms of the Mozilla Public License v2.0 which accompanies this distribution,
and is available at https://www.mozilla.org/en-US/MPL/2.0/
