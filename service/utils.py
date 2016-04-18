from base64 import urlsafe_b64encode
import requests

from service import app


def basic_auth_header():
    """Generate a Globus Auth compatible basic auth header."""
    cid = app.config['GA_CLIENT_ID']
    csecret = app.config['GA_CLIENT_SECRET']

    creds = '{}:{}'.format(cid, csecret)
    basic_auth = urlsafe_b64encode(creds.encode(encoding='UTF-8'))

    return 'Basic ' + basic_auth.decode(encoding='UTF-8')


def token_introspect(token):
    url = app.config['GA_INTROSPECT_URI']

    token_data = requests.post(url,
                               headers=dict(Authorization=basic_auth_header()),
                               data=dict(token=token))

    # response body:
    # {
    #     "active": true,
    #     "scope": "urn:globus:auth:scope:service.example.com:all",
    #     "client_id": "client.example.com",
    #     "sub": "2982f207-04c0-11e5-ac60-22000b92c6ec",
    #     "username": "user1@example.com",
    #     "aud": "server.example.com",
    #     "iss": "https://auth.globus.org/",
    #     "exp": 1419356238,
    #     "iat": 1419350238,
    #     "nbf": 1419350238,
    #     "identities_set": ["2982f207-04c0-11e5-ac60-22000b92c6ec",
    #                        "3982f207-04c0-11e5-ac60-22000b92c6ed"]
    #     "name": "Joe User",
    #     "email": "user1@example.dom"
    # }

    return token_data.json()


def get_token(header):
    return header.split(' ')[1].strip()


def get_dependent_tokens(token):
    url = app.config['GA_TOKEN_URI']
    data = {
        'grant_type': 'urn:globus:auth:grant_type:dependent_token',
        'token': token
    }

    tokens = requests.post(url,
                           headers=dict(Authorization=basic_auth_header()),
                           data=data)

    # response body:
    # [
    #     {
    #         "access_token": "r5qwkEz0lWJdpdknlDBmndC2G7wpTSOk...",
    #         "resource_server": "auth.globus.org",
    #         "scope": "urn:globus:auth:scope:auth.globus.org:view_identities",
    #         "expires_in": 3600,
    #         "refresh_token": "kUKDtLe_xDA4Qxd-ZI-rcFqrBlJj7zXx",
    #         "token_type": "bearer"
    #     },
    #     {
    #         "access_token": "7ZdPhhvija1MUDw6koBYgAAGnbrU79qF...",
    #         "resource_server": "groups.api.globus.org",
    #         "scope": "urn:globus:auth:scope:groups.api.globus.org:[...]",
    #         "expires_in": 3600,
    #         "refresh_token": "dPVJBKAUs0x8UW4zhgQWv6snDmo2X72E",
    #         "token_type": "bearer"
    #     }
    # ]

    return tokens.json()
