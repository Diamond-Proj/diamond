# Diamond: Fine-tune and serve models from one workspace.

![Apache Licence V2.0](https://img.shields.io/badge/License-MIT-yellow.svg) [![NSF award info](https://img.shields.io/badge/NSF-1550588-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=2401245) <!-- TODO: add paper badge -->

[Diamond](https://diamondhpc.ai/) is a platform for training, fine-tuning and serving machine learning models
across [NSF](https://www.nsf.gov/)'s [ACCESS-CI](https://access-ci.org/) resources.

## Deployment

There are 3 modes for deployment and testing:
1. Launch the services independently: Ideal from local dev workflows
2. Launch the services with Docker Compose: Suitable for debugging deployment issues
3. TBD: Deploy to a staging env on AWS with terraform.

### Independent Launch

In this mode, the frontend and backend are launched on a local machine
with the majority of the details specified via `.env` files

Find details in [Frontend README](frontend/README.md) and [Backend README](backend/README.md)

## Launch with Docker Compose

...



