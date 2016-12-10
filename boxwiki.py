import os
import CommonMark
from pyyaml import yaml
from bottle import route, run, hook, request, template, view


__commonmark_version__ = '0.7.2'
__bottle_version__ = '0.12.10'
__pyyaml_version__ = '3.12'
__version__ = '0.0.1'

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
WIKI_DIR = os.path.join(ROOT_DIR, 'wiki')
absjoin = lambda *x: os.path.join(WIKI_DIR, *x)


@route('/')
def index():
    return "Welcome to BoxWiki"


@route('/wiki/<page_path:path>')
@view('page')
def wiki(page_path):
    page_path += '.md'
    page = absjoin(page_path)
    meta, content = _extract(page)
    html = CommonMark.commonmark(content)
    return dict(content=html, title='lol', **meta)


def _extract(fpath):
    meta, content, first_line, meta_parsed = [], [], True, False
    with open(fpath) as fp:
        for line in fp:
            if line.strip() == '---' and first_line: first_line = False
            elif line.strip() == '---' and not first_line and not meta_parsed: meta_parsed = True
            elif not meta_parsed: meta.append(line)
            else: content.append(line)
        try:
            return yaml.load('\n'.join(meta)), ''.join(content)
        except:
            raise SystemExit('File with invalid yaml meta block: ' + fpath)


@hook('before_request')
def strip_path():
    """Removes trailing slashes"""
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


run(reloader=True, host='0.0.0.0', port=3130, debug=True)
