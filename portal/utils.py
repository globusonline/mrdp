from flask import request
from httplib2 import Http
from oauth2client import client as oauth
from threading import Lock

try:
    from urllib.parse import urlparse, urljoin
except:
    from urlparse import urlparse, urljoin

from portal import app


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
    Using our stored credentials, get access tokens we can use to
    perform actions as the identity of the portal rather than the
    identity of the logged-in user.

    A real long-running portal would periodically refresh these access
    tokens when they expire. (Currently, Globus Auth access tokens are
    good for 48 hours.)
    """

    with get_portal_tokens.lock:
        if not get_portal_tokens.access_tokens:
            get_portal_tokens.access_tokens = {}

            for service in ['https', 'transfer', 'service']:
                creds = app.config['PORTAL_CREDS_' + service.upper()]
                creds = oauth.OAuth2Credentials.from_json(creds)
                creds.refresh(Http())
                get_portal_tokens.access_tokens[service] = creds.access_token

        return get_portal_tokens.access_tokens

get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None
