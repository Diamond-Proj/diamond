# Introduction
 
[Diamond](https://diamondhpc.ai/) is a comprehensive web platform built for launching and managing jobs on High-Performance Computing (HPC) infrastructure. It provides a user-friendly interface for submitting jobs, monitoring their progress, and managing resources. This documentation provides an overview of the project structure, setup instructions, and key features.

## Project Overview

Key components of Diamond:

- **Diamond API**: A RESTful API that allows users to submit jobs, monitor their progress, and manage resources.
- **Diamond Web UI**: A web interface that allows users to authenticate, submit jobs, monitor their progress, and manage resources.
- **Globus Compute**: Globus offers a distributed Function as a Service (FaaS) platform that enables reliable, scalable, and high performance remote function execution.
- **Globus Auth**: Globus Auth is a web service that allows users to authenticate and authorize access to resources.
- **Globus Transfer**: Globus Transfer is a web service that allows users to transfer files to and from remote servers.

## Project Infrastructure

- **Diamond API**: A gunicorn server hosted on AWS.
- **Diamond Web UI**: A NextJS application hosted on AWS.
- **Data**: Data is stored in a [PostgreSQL](https://www.postgresql.org/) database hosted on AWS RDS.
- **Services**: 
    - Jobs are executed on [Globus Compute](https://www.globus.org/globus-compute).
    - Files are transferred using [Globus Transfer](https://www.globus.org/globus-transfer).
    - Authentication is handled by [Globus Auth](https://www.globus.org/globus-auth).
