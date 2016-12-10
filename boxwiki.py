import os
import json
import logging
import collections
import CommonMark
from pyyaml import yaml
from bottle import route, run, hook, request, template, view


__commonmark_version__ = '0.7.2'
__bottle_version__ = '0.12.10'
__pyyaml_version__ = '3.12'
__version__ = '0.0.1'

absjoin = lambda x, y: os.path.join(x, y)


@route('/')
def index():
    return "Welcome to BoxWiki"


@route('/wiki/<page_path:path>')
@view('page')
def wiki(page_path):
    page_path += '.md'
    page = wiki.get_abs_path(page_path)
    meta, content = wiki.extract(page)
    html = CommonMark.commonmark(content)
    return dict(content=html, **meta)


class Wiki():
    def __init__(self, ROOT_DIR=os.path.dirname(__file__)):
        self.ROOT_DIR = os.path.abspath(ROOT_DIR)
        self.WIKI_DIR = os.path.join(ROOT_DIR, 'wiki')
        self.set_defaults()
        self.init_site()
        self.watchman = Watchman(self.ROOT_DIR)
        self.mtimes = {}
        self.md2html = CommonMark.commonmark
      
    def set_defaults(self):
        self.config = yaml.load(open(absjoin(self.ROOT_DIR, '_config.yml')).read())

    def init_site(self):
        self.site = collections.defaultdict(list)
        self.site['pages'] = {}
        self.site['ord_pages'] = []
        self.site['categories'] = collections.defaultdict(list)
        self.site['tags'] = collections.defaultdict(list)

    def get_abs_path(self, rfpath):
        return os.path.join(self.WIKI_DIR, rfpath)

    def gen_index(self):
        for root, dirs, files in os.walk(self.WIKI_DIR):
            for fname in files:
                fpath = absjoin(root, fname)
                if fname.endswith('.md'):
                    logging.info("Indexing file: {}".format(fname))
                    meta, text = self.extract(fpath, only_meta=True)
                    page_id = os.path.relpath(fpath, self.WIKI_DIR)
                    meta.update({'slug': os.path.splitext(fname)[0]})
                    self.site['pages'].update({ page_id: meta })
                    for category in meta.get('categories', []):
                        self.site['categories'][category].append(page_id)
                    for tag in meta.get('tags', []):
                        self.site['tags'][tag].append(page_id)
                    self.mtimes[fpath] = os.path.getmtime(fpath)


    def extract(self, fpath, only_meta=False):
        meta, content, first_line, meta_parsed = [], [], True, False
        with open(fpath) as fp:
            try:
                for line in fp:
                    if line.strip() == '---' and first_line:
                        first_line = False
                    elif line.strip() == '---' and not first_line and not meta_parsed:
                        meta_parsed = True
                        if only_meta:
                            return yaml.load('\n'.join(meta)), ''
                    elif not meta_parsed: 
                        meta.append(line)
                    else: 
                        content.append(line)
                return yaml.load('\n'.join(meta)), ''.join(content)
            except:
                raise SystemExit('File with invalid yaml meta block: ' + fpath)


class Watchman():
    def __init__(self, ROOT_DIR):
        logging.info("Watchman awakened.")
        self.ROOT_DIR = ROOT_DIR
        open(absjoin(self.ROOT_DIR, '_mtime.cache'), 'a+').close()
        try:
            with open(absjoin(self.ROOT_DIR, '_mtime.cache'), 'r') as fp:
                self.prev_mtime = json.load(fp)
        except ValueError:
            self.prev_mtime = {}
        logging.info("Read mtime stored during the previous build.")

    def should_build(self, fpath, meta):
        """
        Checks if the file should be built or not
        Only skips layouts which are tagged as INCREMENTAL
        Rebuilds only those files with mtime changed since previous build
        """
        if meta.get('layout', self.default_template) in self.inc_layout:
            if self.prev_mtime.get(fpath, 0) == os.path.getmtime(fpath):
                return False
            else:
                return True
        return True

    def sleep(self, mtimes):
        with open(absjoin(self.ROOT_DIR, '_mtime.cache'), 'w') as fp:
            json.dump(mtimes, fp)
        logging.info("Wrote current mtime into _mtime.cache")


@hook('before_request')
def strip_path():
    """Removes trailing slashes"""
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


if __name__ == '__main__':
    wiki = Wiki()
    run(reloader=True, host='0.0.0.0', port=3130, debug=True)
    logging.basicConfig(filename=absjoin(opts.ROOT_DIR, '_boxwiki.log'), filemode='w', level=logging.DEBUG)
    logging.info("Starting BoxWiki..")
