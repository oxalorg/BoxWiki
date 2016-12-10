import os
import re
import json
import logging
logging.basicConfig(filename='/tmp/boxwiki.log', filemode='w', level=logging.DEBUG)
logging.info("Starting BoxWiki..")
import collections
import CommonMark
from pyyaml import yaml
from bottle import route, run, hook, request, template, view, redirect, \
        static_file


__commonmark_version__ = '0.7.2'
__bottle_version__ = '0.12.10'
__pyyaml_version__ = '3.12'
__version__ = '0.0.1'

absjoin = lambda x, y: os.path.join(x, y)


# Routes

@route('/')
def index():
    return "Welcome to BoxWiki"


@route('/add')
@view('add')
def add():
    return dict(title='Add a new page')


@route('/add', method='POST')
def do_add():
    title = request.forms.get('title')
    category = request.forms.get('category')
    tags = request.forms.getall('tags')
    attachments = request.files.getall('attachments[]')
    content = request.forms.get('content')
    # add a way to add more custom metadata.
    rfpath = wiki.add_page(title=title, category=category, tags=tags, attachments=attachments, content=content)
    return redirect(rfpath)


@route('/static/<filename:path>')
def static(filename):
    print("wow")
    return static_file(filename, root=absjoin(wiki.ROOT_DIR, 'static'))


@route('/wiki/<req_path:path>/edit')
@view('add')
def edit(req_path):
    meta, content = wiki.extract(wiki.get_abs_path(req_path))
    return dict(content=content, **meta)


@route('/test')
def test():
    wiki.gen_index()
    t = wiki.info
    from pprint import pprint
    pprint(t)
    return json.dumps(t)

@route('/wiki')
@view('wiki')
def wiki_index():
    test()
    categories = wiki.info.keys()
    print(wiki.info.keys())
    return dict(categories=categories, title='Wiki')

@route('/wiki/<category>')
@view('category')
def category(category):
    pages = []
    for k, v in wiki.info[category].items():
        print(k, v)
        pages.append(v['meta'])

    if not pages:
        return "Uhoh! No such category exists!"
    return dict(pages=pages, category=category, title=category)


@route('/wiki/<category>/<page:path>')
@route('/wiki/<category>/<page:path>/')
@view('page')
def wiki(category, page, sub=''):
    req_path = "{}/{}".format(category, page)
    fpath = wiki.get_abs_path(req_path)
    print(fpath)
    if os.path.isdir(fpath):
        fpath = absjoin(fpath, 'index.md')
    elif os.path.isfile(fpath + '.md'):
        fpath += '.md'
    elif os.path.exists(fpath):
        return static_file(req_path, root=wiki.WIKI_DIR)
    else:
        return "This page does not exist. Go add it now!"
    meta, content = wiki.extract(fpath)
    attachments = os.listdir(os.path.dirname(fpath))
    html = CommonMark.commonmark(content)
    return dict(content=html, attachments=attachments, **meta)


class Wiki():
    def __init__(self, ROOT_DIR=None):
        self.ROOT_DIR = ROOT_DIR or os.path.abspath(os.path.dirname(__file__))
        self.WIKI_DIR = os.path.join(self.ROOT_DIR, 'wiki')
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
        multilevel_dd = lambda: collections.defaultdict(multilevel_dd)
        self.info = multilevel_dd()

    def get_abs_path(self, *rfpath):
        return os.path.join(self.WIKI_DIR, *rfpath)

    def get_rel_path(self, fpath):
        return os.path.relpath(fpath, self.ROOT_DIR)

    def slugify(self, title):
        slug = [x for x in re.split('[\. ]*', title) if x]
        return '_'.join(slug)

    def add_page(self, title, category, content, tags=[], attachments=[]):
        out = "---\ntitle: {}\ncategory: {}\ntags: {}\n---\n".format(
                title, category, tags)
        out += content
        slug = self.slugify(title)
        fpath = bpath = self.get_abs_path(category, slug)
        fpath = os.path.join(fpath, 'index.md')
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        for upload in attachments:
            print(upload, upload.filename)
            if os.path.exists(absjoin(bpath, upload.filename)):
                logging.error('File exists. Can not overwrite.')
                continue
            upload.save(bpath)

        with open(fpath, 'w') as fp:
            fp.write(out)
        return self.get_rel_path(bpath)

    def gen_index(self):
        for root, dirs, files in os.walk(self.WIKI_DIR):
            parent_dir = os.path.basename(root)
            for fname in files:
                fpath = absjoin(root, fname)
                if fname.endswith('.md'):
                    logging.info("Indexing file: {}".format(fname))
                    meta, _ = self.extract(fpath, only_meta=True)
                    page_id = self.get_rel_path(fpath)
                    if fname == 'index.md':
                        meta.update({'slug': parent_dir})
                        self.info[meta['category']][parent_dir]['meta'] = meta
                    else:
                        meta.update({'slug': os.path.splitext(fname)[0]})
                        self.info[meta['category']][parent_dir][meta['slug']]['meta'] = meta
                    self.site['pages'].update({ page_id: meta })
                    for category in meta.get('category', []):
                        self.site['categories'][category].append(page_id)
                    for tag in meta.get('tags', []):
                        self.site['tags'][tag].append(page_id)
                    self.mtimes[fpath] = os.path.getmtime(fpath)


    def extract(self, fpath, only_meta=False):
        meta, content, first_line, meta_parsed = [], [], True, False
        if os.path.isdir(fpath):
            fpath = absjoin(fpath, 'index.md')
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
    wiki.gen_index()
    run(reloader=True, host='0.0.0.0', port=3130, debug=True)
