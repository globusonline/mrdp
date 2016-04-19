from base64 import urlsafe_b64encode
from flask import request
import requests
from threading import Lock

try:
    from urllib.parse import urlparse, urljoin
except:
    from urlparse import urlparse, urljoin

from portal import app


def basic_auth_header():
    """Generate a Globus Auth compatible basic auth header."""
    auth_config = app.config['GLOBUS_AUTH']
    cid = auth_config['client_id']
    csecret = auth_config['client_secret']

    creds = '{}:{}'.format(cid, csecret)
    basic_auth = urlsafe_b64encode(creds.encode(encoding='UTF-8'))

    return 'Basic ' + basic_auth.decode(encoding='UTF-8')


def is_safe_redirect_url(target):
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc


def get_safe_redirect():
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    url = request.args.get('next')
    if url and is_safe_redirect_url(url):
        return url

    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url

    return '/'


def get_portal_tokens():
    """
    Using our stored refresh tokens, get access tokens we can use to
    perform actions as the identity of the portal rather than the
    identity of the logged-in user.

    A real long-running portal would periodically refresh these access
    tokens when they expire. (Currently, Globus Auth access tokens are
    good for 48 hours.)

    FIXME. Once the Auth API is patched to work with client ID/secret within
    the body of the POST, replace `PORTAL_REFRESH_TOKEN_XXX` with serialized
    refresh tokens (i.e. using `credentials.to_json()`) and use the Google
    `oauth2client` library to get the access token here.
    """

    with get_portal_tokens.lock:
        if not get_portal_tokens.access_tokens:
            get_portal_tokens.access_tokens = {}

            for service in ['https', 'transfer', 'service']:
                refresh_token = app.config['PORTAL_REFRESH_TOKEN_' +
                                           service.upper()]
                get_portal_tokens.access_tokens[service] = requests.post(
                    app.config['GLOBUS_AUTH']['token_uri'],
                    data=dict(grant_type='refresh_token',
                              refresh_token=refresh_token),
                    headers=dict(Authorization=basic_auth_header()),
                ).json()['access_token']

        return get_portal_tokens.access_tokens

get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None
