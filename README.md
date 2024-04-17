# Globus Sample Data Portal: A Modern Research Data Portal Implementation

A Python (Flask-based) web application demonstrating how to build a [Modern Research Data Portal](https://docs.globus.org/guides/recipes/modern-research-data-portal/) using
the [Globus platform](https://www.globus.org/platform).

## Overview
This repository contains two separate server applications. The first, the "portal," is an example "research portal"
that demonstrates how to authenticate users with [Globus Auth](https://docs.globus.org/api/auth/), how to make requests against the [Globus Transfer API](https://docs.globus.org/api/transfer/), and how to interact with an HTTPS-enabled Globus collection. All of the portal code can be found in the `portal/` directory.

The second application, the "Service," is an example "resource server" that demonstrates how a research portal can offload tasks to a separate service that has the capability to perform tasks on behalf of users. All of the Service code can be found in the `service/` directory.

`Note`: Both applications are configured with client credentials created for demo purposes only.

## Getting Started
The Globus Sample Data Portal requires Python 3.9 or newer.

#### Set up your environment.
* [OS X](#os-x)
* [Linux](#linux-ubuntu)
* [Windows](#windows)
* [Amazon EC2](#amazon-ec2)
* [Reverse Proxy with Nginx](#reverse-proxy-with-nginx)

#### Register a Globus Application for use in the Portal. 
* [Register an Application with Globus](https://docs.globus.org/api/auth/developer-guide/#register-app)
* When registering the App you'll be asked for some information, including the redirect URL and any scopes you will be requesting.
    * Redirect URL: `https://localhost:5000/authcallback` (note: if using EC2 `localhost` should be replaced with the IP address of your instance).
    * Scopes: `urn:globus:auth:scope:transfer.api.globus.org:all`, `openid`, `profile`, `email`
* After creating your App the client id and secret can be copied into this project in the following two places:
    * `portal/portal.conf` in the `PORTAL_CLIENT_ID` and `PORTAL_CLIENT_SECRET` properties.
    * `service/service.conf` where the `PORTAL_CLIENT_ID` is used to validate the access token that the Portal sends to the Service.

### OS X

##### Environment Setup

* Install python3
* `git clone https://github.com/globus/globus-sample-data-portal`
* `cd globus-sample-data-portal`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`

##### Running the Portal App

* `./run_portal.py`
* point your browser to `https://localhost:5000`

##### Running the Service App

* `./run_service.py`
* API is located at `https://localhost:5100/api`

### Linux (Ubuntu)

##### Environment Setup

* `sudo apt-get update`
* `sudo apt-get install python3-pip`
* `sudo pip install virtualenv`
* `sudo apt-get install git`
* `git clone https://github.com/globus/globus-sample-data-portal`
* `cd globus-sample-data-portal`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`

##### Running the Portal App

* `./run_portal.py`
* point your browser to `https://localhost:5000`

##### Running the Service App

* `./run_service.py`
* API is located at `https://localhost:5100/api`

### Windows

##### Environment Setup

* Install Python3 (<https://www.python.org/downloads/windows/>)
* `pip install virtualenv`
* Install git (<https://git-scm.com/downloads>)
* `git clone https://github.com/globus/globus-sample-data-portal`
* `cd globus-sample-data-portal`
* `virtualenv venv`
* `venv\Scripts\activate`
* `pip install -r requirements.txt`

##### Running the Portal App

* `python run_portal.py`
* point your browser to `https://localhost:5000`

##### Running the Service App

* `python run_service.py`
* API is located at `https://localhost:5100/api`

### Amazon EC2

##### Environment Setup

* `git clone https://github.com/globus/globus-sample-data-portal`
* `cd globus-sample-data-portal`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`
* `sed -i 's/localhost/0.0.0.0/' run_portal.py`
* `sed -i '4,//s/localhost/YOUR_IP/' portal/portal.conf`
* `echo "SESSION_COOKIE_DOMAIN = 'YOUR_IP'" >> portal/portal.conf`

##### Running the Portal App

* `./run_portal.py`
* point your web browser to `https://YOUR_IP:5000/`

##### Running the Service App

* `./run_service.py`
* API is located at `https://localhost:5100/api`

### Reverse Proxy with Nginx

Deploying and fully configuring Nginx is out of scope of this document. However, if you wish to use Nginx as a reverse proxy, you can use the location block below:
```
  location / {
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Prefix /;
    proxy_pass https://localhost:5000/;
  }
```
