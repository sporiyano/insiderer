#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import math
if sys.version_info[0] < 3:
    raise "Must be using Python 3"
import magic
ms = magic.open(magic.MAGIC_NONE)
ms.load()
ms.setflags(magic.MAGIC_MIME)
import re
import os.path
import optparse
import tempfile
import socket
import cherrypy

# START DEFAULT CONFIG
host='0.0.0.0'
port=443
# END CONFIG
parser = optparse.OptionParser()
parser.add_option("-p", "--port", dest="port", help="Port", type="int")
parser.add_option("-H", "--host", dest="host", help="Host/IP", type="str")
(options, args) = parser.parse_args()
if options.port:
    port = options.port
if options.host:
    host = options.host

class Site(object):
  exposed = True

  def GET(self):
    return '<!DOCTYPE html><link rel="stylesheet" href="static/screen.css"><body><div id=logo><img src="static/insiderer.png" width=419></div><form method=post enctype=multipart/form-data><span>Choose file(s)</span><input type=file name=a id=files multiple></form><div id=loading></div><script type="text/javascript" src="static/index.js"></script>'

  @cherrypy.tools.json_out()
  def POST(self, **kwargs):
    metadata_files = []
    for key, postfile in kwargs.items():
      try:
        tmp_path = tempfile.mkstemp(dir='/run/')[1]
        handle = open(tmp_path, 'wb')
        handle.write(postfile.file.read())
        handle.close()
        metadata = get_metadata(tmp_path, postfile.filename)
        metadata_files.append(metadata)
      except Exception as e:
        print("EXCEPTION", e)
        pass
      finally:
        safedelete(tmp_path)
    return metadata_files;

def get_metadata(path, filename):
    def sanitise(mimetype):
        return re.sub(r'[^a-z]', '_', mimetype)

    def sha1OfFile(filepath):
        import hashlib
        sha = hashlib.sha1()
        if os.path.isdir(filepath):
            return None
        with open(filepath, 'rb') as f:
            while True:
                block = f.read(2**10) # Magic number: one-megabyte blocks.
                if not block: break
                sha.update(block)
            return sha.hexdigest()

    mimetype = ms.file(path)

    filedata = {}
    filedata['filename'] = filename;
    filedata['mimetype'] = mimetype;
    filedata['sha1'] = sha1OfFile(path);
    filedata['filesize_bytes'] = os.path.getsize(path);
    filedata['children'] = [];
    mime_app = None;

    mime_app_name = sanitise(mimetype.split(";")[0])
    import_obj = 'mimes.%s' % mime_app_name
    if not os.path.exists(import_obj.replace('.', '/') + ".py"):
        mime_app_name = sanitise(mimetype.split("/")[0])
        import_obj =  'mimes.%s' % mime_app_name
        if not os.path.exists(import_obj.replace('.', '/') + ".py"):
            import_obj = None

    if import_obj:
        mime_app = __import__(import_obj)

    if mime_app: #if there was a handler for this mimetype
        mime_app_method = getattr(mime_app, mime_app_name)
        filedata['metadata'] = {}
        getattr(mime_app_method, mime_app_name)(path, filedata['metadata'], filedata['children'])
    if len(filedata['children']) == 0:
        del filedata['children']
    return filedata


def safedelete(path):
    if os.path.isdir(path):
      print("Can't safedelete directory", path)
      return
    sector = 4096
    data = ""
    try:
      filesize = os.path.getsize(path)
      cycles = math.ceil(filesize / sector) + 1
      with open(path, 'wb') as safehandle:
        safehandle.seek(0)
        for x in range(0, cycles):
          safehandle.write(os.urandom(sector))
    except Exception as e:
      print(e)
    finally:
      os.unlink(path)
    

if __name__ == '__main__':
  conf = {
      'global': {
           'server.socket_host': host,
           'server.socket_port': port,
           'server.ssl_module': 'builtin',
           'server.ssl_certificate': '../docvert2015httpscert.pem',
           'server.ssl_private_key': '../docvert2015https.pem'
      },
      '/': {
          'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
          'tools.staticdir.root': os.path.abspath(os.getcwd())
      },
      '/static': {
          'tools.staticdir.on': True,
          'tools.staticdir.dir': './static'
      }
  }
  cherrypy.quickstart(Site(), '/', conf)



