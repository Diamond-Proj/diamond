# Diamond Admin Backend

## Overview

Diamond Admin Backend is a admin Flask server integrating SQLite for database management.

## Installation Instructions

### Prerequisites

- Python 3

### Setting Up the Project

1. **Clone the repository:**

   ```bash
   git clone [repository-url]
   cd [repository-directory]
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

   - Copy the `.env.example` file to `.env` and adjust the configuration to match your local setup for both backend and frontend.

4. **Running the Development Servers:**

   - Start the Flask backend:
     ```bash
     pnpm run flask-dev
     ```

5. **Access the Application:**
   - Open your web browser and navigate to `http://localhost:5328` to view the dashboard.

## Additional Information

- Ensure all environment variables and configurations are set correctly in the `.env` file for both the backend and frontend services.

<br>

Copyright (c) 2024 University of Illinois and others. All rights reserved.

This program and the accompanying materials are made available under the
terms of the Mozilla Public License v2.0 which accompanies this distribution,
and is available at https://www.mozilla.org/en-US/MPL/2.0/
