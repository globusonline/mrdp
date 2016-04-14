import uuid

from flask import (abort, flash, g, redirect, render_template, request,
                   session, url_for)
from oauth2client import client as oauth
import requests

try:
    from urllib.parse import urlencode
except:
    from urllib import urlencode

from globus_sdk import TransferClient, TransferAPIError

from mrdp import app, database, datasets
from mrdp.decorators import authenticated
from mrdp.processing import render_graphs
from mrdp.utils import basic_auth_header, get_safe_redirect, get_portal_tokens


@app.route('/', methods=['GET'])
def home():
    """Home page - play with it if you must!"""
    return render_template('home.jinja2')


@app.route('/signup', methods=['GET'])
def signup():
    """Send the user to Globus Auth with signup=1."""
    return redirect(url_for('authcallback', signup=1))


@app.route('/login', methods=['GET'])
def login():
    """Send the user to Globus Auth."""
    return redirect(url_for('authcallback'))


@app.route('/logout', methods=['GET'])
@authenticated
def logout():
    """
    Add code here to:

    - Revoke Globus Auth token(s).
    - Destroy the session.
    - Redirect the user to the Globus Auth logout page.
    """
    headers = {'Authorization': basic_auth_header()}
    data = {
        'token_type_hint': 'refresh',
        'token': g.credentials.refresh_token
    }

    # If we don't get support for POST body client credentials,
    # add a commented out example of using the oauth2client revoke
    # method.

    # Invalidate the tokens with Globus Auth
    requests.post(app.config['GA_REVOKE_URI'],
                  headers=headers,
                  data=data)

    # Destroy the session state
    session.clear()

    redirect_uri = url_for('home', _external=True)

    ga_logout_url = []
    ga_logout_url.append(app.config['GA_LOGOUT_URI'])
    ga_logout_url.append('?client={}'.format(app.config['GA_CLIENT_ID']))
    ga_logout_url.append('&redirect_uri={}'.format(redirect_uri))
    ga_logout_url.append('&redirect_name=MRDP Demo App')

    # Send the user to the Globus Auth logout page
    return redirect(''.join(ga_logout_url))


@app.route('/profile', methods=['GET', 'POST'])
@authenticated
def profile():
    """User profile information. Assocated with a Globus Auth identity."""
    if request.method == 'GET':
        identity_id = session.get('primary_identity')
        profile = database.load_profile(identity_id)

        if profile:
            name, email, project = profile

            session['name'] = name
            session['email'] = email
            session['project'] = project

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.jinja2')
    elif request.method == 'POST':
        name = session['name'] = request.form['name']
        email = session['email'] = request.form['email']
        project = session['project'] = request.form['project']

        database.save_profile(identity_id=session['primary_identity'],
                              name=name,
                              email=email,
                              project=project)

        flash('Thank you! Your profile has been successfully updated.')

        if 'next' in session:
            redirect_to = session['next']
            session.pop('next')
        else:
            redirect_to = url_for('profile')

        return redirect(redirect_to)


@app.route('/authcallback', methods=['GET'])
def authcallback():
    """Handles the interaction with Globus Auth."""
    # If we're coming back from Globus Auth in an error state, the error
    # will be in the "error" query string parameter.
    if 'error' in request.args:
        pass
        # handle error

    # Set up our Globus Auth/OAuth2 state

    scopes = 'urn:globus:auth:scope:transfer.api.globus.org:all'
    config = app.config

    if request.args.get('signup'):
        authorize_uri = '{}?signup=1'.format(config['GA_AUTH_URI'])
    else:
        authorize_uri = config['GA_AUTH_URI']

    flow = oauth.OAuth2WebServerFlow(app.config['GA_CLIENT_ID'],
                                     scope=scopes,
                                     authorization_header=basic_auth_header(),
                                     redirect_uri=config['GA_REDIRECT_URI'],
                                     auth_uri=authorize_uri,
                                     token_uri=config['GA_TOKEN_URI'],
                                     revoke_uri=config['GA_REVOKE_URI'])

    # If there's no "code" query string parameter, we're in this route
    # starting a Globus Auth login flow.
    if 'code' not in request.args:
        state = str(uuid.uuid4())

        auth_uri = flow.step1_get_authorize_url(state=state)

        session['oauth2_state'] = state

        return redirect(auth_uri)
    else:
        # If we do have a "code" param, we're coming back from Globus Auth
        # and can start the process of exchanging an auth code for a token.
        passed_state = request.args.get('state')

        if passed_state and passed_state == session.get('oauth2_state'):
            code = request.args.get('code')

            try:
                credentials = flow.step2_exchange(code)
            except Exception as err:
                return repr(err)
            else:
                session.pop('oauth2_state')

                id_token = credentials.id_token
                session.update(
                    credentials=credentials.to_json(),
                    is_authenticated=True,
                    primary_username=id_token.get('preferred_username'),
                    primary_identity=id_token.get('sub'),
                )

            return redirect(url_for('transfer'))


@app.route('/transfer', methods=['GET', 'POST'])
@authenticated
def transfer():
    """
    Add code here to:

    - Save the submitted form to the session.
    - Send to Globus to select a destination endpoint using the
      Browse Endpoint helper page.
    """
    if request.method == 'GET':
        return render_template('transfer.jinja2', datasets=datasets)

    if request.method == 'POST':
        if not request.form.get('dataset'):
            flash('Please select at least one dataset.')
            return redirect(url_for('transfer'))

        params = {
            'method': 'POST',
            'action': url_for('submit_transfer', _external=True,
                              _scheme='https'),
            'filelimit': 0,
            'folderlimit': 1
        }

        browse_endpoint = 'https://www.globus.org/app/browse-endpoint?{}' \
            .format(urlencode(params))

        session['form'] = {
            'datasets': request.form.getlist('dataset')
        }

        return redirect(browse_endpoint)


@app.route('/submit-transfer', methods=['POST'])
@authenticated
def submit_transfer():
    """
    Add code here to:

    - Take the data returned by the Browse Endpoint helper page
      and make a Globus transfer request.
    - Send the user to the transfer status page with the task id
      from the transfer.
    """
    globus_form = request.form

    selected = session['form']['datasets']
    filtered_datasets = [ds for ds in datasets if ds['id'] in selected]

    transfer = TransferClient(token=g.credentials.access_token)

    source_endpoint_id = app.config['DATASET_ENDPOINT_ID']
    source_endpoint_base = app.config['DATASET_ENDPOINT_BASE']
    destination_endpoint_id = globus_form['endpoint_id']

    transfer_items = []
    for ds in filtered_datasets:
        source_path = source_endpoint_base + ds['path']
        dest_path = globus_form['path']

        if globus_form.get('folder[0]'):
            dest_path += globus_form['folder[0]'] + '/'

        dest_path += ds['name'] + '/'

        transfer_items.append({
            'DATA_TYPE': 'transfer_item',
            'source_path': source_path,
            'destination_path': dest_path,
            'recursive': True
        })

    submission_id = transfer.get_submission_id()['value']
    transfer_data = {
        'DATA_TYPE': 'transfer',
        'submission_id': submission_id,
        'source_endpoint': source_endpoint_id,
        'destination_endpoint': destination_endpoint_id,
        'label': globus_form.get('label') or None,
        'DATA': transfer_items
    }

    transfer.endpoint_autoactivate(source_endpoint_id)
    transfer.endpoint_autoactivate(destination_endpoint_id)
    task_id = transfer.submit_transfer(transfer_data)['task_id']

    flash('Transfer request submitted successfully. Task ID: ' + task_id)

    return(redirect(url_for('transfer_status', task_id=task_id)))


@app.route('/graph', methods=['GET', 'POST'])
@authenticated
def graph():
    """
    Add code here to:

    - Read the year and the IDs of the datasets the user wants
    - Instantiate a Transfer client as the identity of the portal
    - `GET` the CSVs for the selected datasets via HTTPS server as the
      identity of the portal
    - Generate a graph SVG file for the precipitation (`PRCP`) and
      temperature (`TMIN`/`TMAX`) for the selected year and datasets
    - `PUT` the generated graphs onto the predefined share endpoint as
      the identity of the portal
    - Display a confirmation
    """

    if request.method == 'GET':
        return render_template('graph.jinja2', datasets=datasets)

    selected_ids = request.form.getlist('dataset')
    selected_datasets = [dataset for dataset in datasets
                         if dataset['id'] in selected_ids]
    selected_year = request.form.get('year')

    if not (selected_datasets and selected_year):
        flash("Please select at least one dataset and a year to graph.")
        return redirect(url_for('graph'))

    transfer_token = get_portal_tokens()['transfer']
    https_token = get_portal_tokens()['https']

    transfer = TransferClient(token=transfer_token)

    source_ep = app.config['DATASET_ENDPOINT_ID']
    source_info = transfer.get_endpoint(source_ep)
    source_https = source_info['https_server']
    source_base = app.config['DATASET_ENDPOINT_BASE']
    source_token = https_token

    dest_ep = app.config['GRAPH_ENDPOINT_ID']
    dest_info = transfer.get_endpoint(dest_ep)
    dest_https = dest_info['https_server']
    dest_base = app.config['GRAPH_ENDPOINT_BASE']
    dest_path = '%sGraphs for %s/' % (dest_base, session['primary_username'])
    dest_token = https_token

    if not (source_https and dest_https):
        flash("Both dataset and graph endpoints must be HTTPS endpoints.")
        return redirect(url_for('graph'))

    svgs = {}

    for dataset in selected_datasets:
        source_path = dataset['path']
        response = requests.get('%s%s%s/%s.csv' % (source_https, source_base,
                                                   source_path, selected_year),
                                verify=False,  # FIXME
                                headers=dict(
                                    Authorization='Bearer ' + source_token,
                                ),
                                allow_redirects=False)
        response.raise_for_status()
        svgs.update(render_graphs(
            csv_data=response.iter_lines(decode_unicode=True),
            append_titles=" from %s for %s" % (dataset['name'], selected_year),
        ))

    transfer.endpoint_autoactivate(dest_ep)

    try:
        transfer.operation_mkdir(dest_ep, dest_path)
    except TransferAPIError as error:
        if 'MkdirFailed.Exists' not in error.code:
            raise

    try:
        transfer.add_endpoint_acl_rule(
            dest_ep,
            dict(principal=session['primary_identity'],
                 principal_type='identity', path=dest_path, permissions='r'),
        )
    except TransferAPIError as error:
        if error.code != 'Exists':
            raise

    for filename, svg in svgs.items():
        # TODO Does the HTTPS server throw an error for an already-existing
        # destination file, or is it silently overwritten?
        requests.put('%s%s%s.svg' % (dest_https, dest_path, filename),
                     data=svg,
                     verify=False,  # FIXME
                     headers=dict(
                        Authorization='Bearer ' + dest_token,
                     ),
                     allow_redirects=False).raise_for_status()

    flash("%d-file SVG upload to %s on %s completed!" %
          (len(svgs), dest_path, dest_info['display_name']))
    return redirect(url_for('browse', endpoint_id=dest_ep,
                            endpoint_path=dest_path.lstrip('/')))


@app.route('/graph/clean-up', methods=['POST'])
@authenticated
def graph_cleanup():
    """
    Add code here to:

    - figure out the logged-in user's graph directory
    - find the logged-in user's ACL for the graph directory
    - delete both the directory and the associated ACL
    """

    transfer_token = get_portal_tokens()['transfer']
    transfer = TransferClient(token=transfer_token)

    dest_ep = app.config['GRAPH_ENDPOINT_ID']
    dest_base = app.config['GRAPH_ENDPOINT_BASE']
    dest_path = '%sGraphs for %s/' % (dest_base, session['primary_username'])

    try:
        acl = next(acl for acl in transfer.endpoint_acl_list(dest_ep)
                   if dest_path == acl['path'])
    except StopIteration:
        pass
    else:
        transfer.delete_endpoint_acl_rule(dest_ep, acl['id'])

    submission_id = transfer.get_submission_id()['value']

    delete_request = dict(
        DATA_TYPE='delete',
        endpoint=dest_ep,
        ignore_missing=True,
        interpret_globs=False,
        label="Delete Processed Graphs from the Data Portal Demo",
        recursive=True,
        submission_id=submission_id,

        DATA=[dict(
            DATA_TYPE='delete_item',
            path=dest_path,
        )],
    )

    transfer.submit_delete(delete_request)

    flash("Your existing processed graphs have been removed.")
    return redirect(url_for('graph'))


@app.route('/browse/dataset/<dataset_id>', methods=['GET'])
@app.route('/browse/endpoint/<endpoint_id>/<path:endpoint_path>',
           methods=['GET'])
@authenticated
def browse(dataset_id=None, endpoint_id=None, endpoint_path=None):
    """
    Add code here to:

    - Get list of files for the selected dataset or endpoint ID/path
    - Return a list of files to a browse view

    The target template (browse.jinja2) expects an `endpoint_uri` (if
    available for the endpoint), `target` (either `"dataset"`
    or `"endpoint"`), and 'file_list' (list of dictionaries) containing
    the following information about each file in the result:

    {'name': 'file name', 'size': 'file size', 'id': 'file uri/path'}

    If you want to display additional information about each file, you
    must add those keys to the dictionary and modify the browse.jinja2
    template accordingly.
    """

    assert bool(dataset_id) != bool(endpoint_id and endpoint_path)

    if dataset_id:
        try:
            dataset = next(ds for ds in datasets if ds['id'] == dataset_id)
        except StopIteration:
            abort(404)

        endpoint_id = app.config['DATASET_ENDPOINT_ID']
        endpoint_path = app.config['DATASET_ENDPOINT_BASE'] + dataset['path']

    else:
        endpoint_path = '/' + endpoint_path

    transfer = TransferClient(token=g.credentials.access_token)

    try:
        transfer.endpoint_autoactivate(endpoint_id)
        listing = transfer.operation_ls(endpoint_id, path=endpoint_path)
    except TransferAPIError as err:
        flash('Error [{}]: {}'.format(err.code, err.message))
        return redirect(url_for('transfer'))

    file_list = [e for e in listing if e['type'] == 'file']

    ep = transfer.get_endpoint(endpoint_id)

    https_server = ep['https_server']
    endpoint_uri = https_server + endpoint_path if https_server else None
    webapp_xfer = 'https://www.globus.org/app/transfer?' + \
        urlencode(dict(origin_id=endpoint_id, origin_path=endpoint_path))

    return render_template('browse.jinja2', endpoint_uri=endpoint_uri,
                           target="dataset" if dataset_id else "endpoint",
                           description=(dataset['name'] if dataset_id
                                        else ep['display_name']),
                           file_list=file_list, webapp_xfer=webapp_xfer)


@app.route('/status/<task_id>', methods=['GET'])
@authenticated
def transfer_status(task_id):
    """
    Add code here to call Globus to get status/details of transfer with
    task_id.

    The target template (tranfer_status.jinja2) expects a 'task_id'
    (str) and a 'transfer_status' (dictionary) containing various
    details about the task. 'transfer_status' is expected to contain the
    following keys:

    {
        'source_ep_name': 'display name of source endpoint',
        'dest_ep_name': 'display name of destination endpoint',
        'request_time': time that the transfer request was submitted,
        'status': 'status of the transfer task',
        'files_transferred': number of files transferred so far,
        'fault': number of faults encountered,
    }

    'task_id' is passed to the route in the URL as 'task_id'.

    If you want to display additional information about the transfer,
    you must add those keys to the dictionary and modify the
    transfer_status.jinja2 template accordingly.
    """
    transfer = TransferClient(token=g.credentials.access_token)
    task = transfer.get_task(task_id)

    return render_template('transfer_status.jinja2', task=task)
