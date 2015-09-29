#!/usr/bin/python2
"""
Generate a webpage to collect relation data for dynamic endpoints.


"""
import sys
sys.path.insert(0, 'lib')

import pkg_resources

import tornado.auth
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.template
import tornado.web
import logging
from json import loads, dumps
import os
from path import path
import subprocess
from charmhelpers import hookenv

SAVED_ENV = {}


class JSONDB(list):
    def __init__(self, filename="endpoints.json"):
        self.filename = path(filename)
        if not self.filename.exists():
            self.filename.write_text("[]\n")
        self.load()

    def load(self):
        del self[:]
        data = loads(open(self.filename, "r").read())
        self.extend(data)

    def save(self):
        with open(self.filename, "w") as fp:
            fp.write(dumps(self))
            fp.flush()

    def lookup(self, name):
        for item in self:
            if item['name'] == name:
                return item
        return {}

    def update(self, data):
        match = None
        for i, item in enumerate(self):
            if data["name"] == item["name"]:
                match = i
                break
        if match:
            del self[match]
        self.append(data)
        self.save()

    def replaceAll(self, data):
        del self[:]
        self.extend(data)
        self.save()

    def remove(self, data):
        match = None
        for i, item in enumerate(self):
            if data["name"] == item["name"]:
                match = i
                break
        if match:
            del self[match]
        self.save()


class JSONDBwHooks(JSONDB):
    HOOK = """!/bin/bash
relation-set {}
"""

    def save(self):
        super(JSONDBwHooks, self).save()
        # post save we need to iterate the data and update any hooks
        # if the relation already exists we should subsequently invoke the hook
        charm_dir = os.environ.get("CHARM_DIR", "")
        hookdir = path(charm_dir) / "hooks"
        # XXX: we don't prune old hook files
        for e in self:
            hookname = "{}-relation-changed".format(e['name'])
            hook = hookdir / hookname
            reldata = ' '.join(['{}="{}"'.format(k, v) for k, v in \
                                e['data'].items()])
            hook.write_text(self.HOOK.format(reldata))
            hook.chmod("a+rx")
        # XXX: we call this sync for now, this should be very low
        # contention in the prototype
        # XXX: this fails silently and allows for failure in the case
        # of already added endpoints
            if charm_dir:
                subprocess.check_call(['endpoint-add',
                                       e['name'],
                                       e['interface']],
                                      env=SAVED_ENV)
                rid = hookenv.relation_ids(e['name'])
                if rid:
                    hookenv.relation_set(rid, e['data'])


class RequestBase(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.settings['db']


class RestBase(RequestBase):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")


ENDPOINT_SCHEMA = {
    "type": "object",
    "title": "Endpoint",
    "defaultProperties": ["name", "interface", "data"],
    "properties": {
        "name": {
            "type": "string"
        },
        "interface": {
            "type": "string"
        },
        "data": {
            "type": "object"
        }
    }
}


class SchemaHandler(RestBase):
    def get(self):
        self.write(dumps(ENDPOINT_SCHEMA, indent=2))


class EndpointsHandler(RestBase):
    @tornado.web.addslash
    def get(self):
        self.write(dumps(self.db))

    @tornado.web.addslash
    def post(self, data):
        self.db.replaceAll(data)


class EndpointHandler(RestBase):
    @tornado.web.addslash
    def get(self, name):
        data = self.db.lookup(name)
        self.write(dumps(data))

    @tornado.web.addslash
    def post(self):
        body = loads(self.request.body.decode("utf-8"))
        self.db.update(body)

    @tornado.web.addslash
    def delete(self):
        body = loads(self.request.body.decode("utf-8"))
        self.db.remove(body)


class MainHandler(RequestBase):
    def get(self):
        return self.render("index.html")


def load_saved_env(filename="environment.sh"):
    env = {}
    for line in path(filename).lines():
        key, value = line.split("=", 1)
        env[key] = value
    SAVED_ENV.update(env)


def main():
    settings = dict(
        autoreload=True,
        debug=True,
        login_url="/login",
        template_path=pkg_resources.resource_filename(__name__, "."),
        static_path=pkg_resources.resource_filename(__name__, "static"),
        db=JSONDBwHooks(),
    )
    # config-changed should have saved off the juju env
    # needed for the hook tool to run
    load_saved_env()

    application = tornado.web.Application([
        (r"/endpoint/?", EndpointHandler),
        (r"/endpoints/?", EndpointsHandler),
        (r"/schema/?", SchemaHandler),
        (r"/", MainHandler),
    ], **settings)

    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    logging.basicConfig()
    main()
