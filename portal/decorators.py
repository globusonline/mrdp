from flask import g, redirect, request, session, url_for
from functools import wraps
from oauth2client import client as oauth

from portal import database


def authenticated(fn):
    """Mark a route as requiring authentication."""
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))

        g.credentials = oauth.OAuth2Credentials.from_json(
            session['credentials'])

        profile = database.load_profile(session['primary_identity'])

        if profile:
            name, email, project = profile
            session['name'] = name
            session['email'] = email
            session['project'] = project
        else:
            session['name'] = g.credentials.id_token.get('name', '')
            session['email'] = g.credentials.id_token.get('email', '')
            session['project'] = g.credentials.id_token.get('project', '')

            if request.path != '/profile':
                return redirect(url_for('profile', next=request.url))

        return fn(*args, **kwargs)
    return decorated_function
