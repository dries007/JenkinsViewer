import re
import os
import time

import flask
import html_sanitizer
import requests
from werkzeug import exceptions


app = flask.Flask(__name__)
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True


SECOND_CLASS_ARTIFACT = re.compile(r'.*-(sources|src|deobf|dev|lib).*\.jar$')


def h_replacer(element):
    if element.tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
        element.tag = 'p'
    return element


sanitizer = html_sanitizer.Sanitizer()
sanitizer.element_preprocessors.append(h_replacer)


HOST = f'http://{os.getenv("JENKINS", "127.0.0.1:8090")}/'

TREE_BUILD = 'id,timestamp,artifacts[*],url'
TREE_JOB_BASE = 'name,description,scm[userRemoteConfigs[url]]'
TREE_JOBS = f'{TREE_JOB_BASE},lastSuccessfulBuild[{TREE_BUILD}]'
TREE_JOB = f'{TREE_JOB_BASE},allBuilds[{TREE_BUILD},building,description,result,changeSet[items[commitId,comment]]]'

URL_JOBS = f'{HOST}api/json?tree=jobs[{TREE_JOBS}]'
URL_JOB = f'{HOST}job/%s/api/json?tree={TREE_JOB}'
URL_BUILD = f'{HOST}job/%s/%s/artifact/%s'


@app.template_filter('ctime')
def filter_ctime(s: int):
    return time.strftime('%Y-%m-%d %H:%M', time.gmtime(s))


@app.template_filter('sanitize')
def filter_sanitize(s: str):
    return flask.Markup(sanitizer.sanitize(s))


@app.template_filter('nl2br')
def filter_nl2br(s: str):
    return flask.Markup(s.replace('\n', '<br/>'))


@app.template_filter('is_secondary_artifact')
def filter_is_secondary_artifact(s: str):
    return s.endswith('.json') or SECOND_CLASS_ARTIFACT.fullmatch(s) is not None


@app.template_filter('sort_artifacts')
def filter_sort_artifacts(artifacts: [dict]):
    def _key(a: dict):
        name = a['fileName']
        modifier = 0
        if name.endswith('.json'):
            modifier = 100000
        elif filter_is_secondary_artifact(name):
            modifier = 10000
        return len(name) + modifier

    return sorted(artifacts, key=_key)


def object_hook(obj: dict):
    banned = {'_class', 'actions'}
    for x in banned:
        obj.pop(x, None)
    if not obj:
        return
    return obj


@app.errorhandler(Exception)
def any_error(e: Exception):
    if isinstance(e, exceptions.HTTPException):
        return flask.render_template('error.html', description=e.description, code=e.code), e.code
    if isinstance(e, requests.exceptions.RequestException):
        return flask.render_template('error.html', description=e.__class__.__name__, code=500), 500
    print("ERROR", type(e), str(e), repr(e))
    return flask.render_template('error.html', description=str(e), code=500), 500


def make_error(r: requests.Response):
    if r.status_code == 404:
        description = 'The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.'
    elif r.status_code == 503:
        description = 'The server is temporarily unable to service your request due to maintenance downtime or capacity problems. Please try again later.'
    elif r.status_code == 504:
        description = 'The connection to an upstream server timed out.'
    else:
        description = 'An error has occurred.'
    return flask.render_template('error.html', description=description, code=r.status_code), r.status_code


@app.route('/')
def route_root():
    # print(URL_JOBS)
    r = requests.get(URL_JOBS)
    if r.status_code >= 400:
        return flask.render_template('error.html', description='Something is wrong with the backend server.', code=r.status_code), r.status_code
    jobs: list = r.json()['jobs']
    jobs.sort(key=lambda x: -x['lastSuccessfulBuild']['timestamp'])
    return flask.render_template('index.html', jobs=jobs)


@app.route('/<string:project>')
def route_project(project: str):
    # print(URL_JOB % project)
    r = requests.get(URL_JOB % project)
    if r.status_code >= 400:
        return make_error(r)
    return flask.render_template('project.html', job=r.json())


@app.route('/<string:project>/<string:build>/<path:file>')
def route_file(project: str, build: str, file: str):
    # print(URL_BUILD % (project, build, file))
    if '/../' in file:
        raise exceptions.BadRequest('No /../ allowed in URLs.')
    r = requests.get(URL_BUILD % (project, build, file))
    if r.status_code >= 400:
        return make_error(r)
    return flask.Response(r.content, mimetype=r.headers['content-type'])


if __name__ == '__main__':
    app.run()
