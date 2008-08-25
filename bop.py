import wsgiref.handlers
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
import datetime
import time
from models import Row, Marker
import logging
import formencode
from formencode import htmlfill
from google.appengine.api import users

class Generic(db.Expando):
    dt = db.DateTimeProperty()
    name = db.StringProperty()
    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.name)

class Bop(webapp.RequestHandler):
    def get(self):
        a = Generic(dt=datetime.datetime.now(), name='poop', alpha='qq')
        a.put()
        b = Generic(dt=datetime.datetime.now(), name='prk', beta='ww')
        b.put()
        c = Generic(dt=datetime.datetime.now(), name='pnd', alpha='ss')
        c.put()
        q = Generic.all().filter('alpha >', '')
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('%s' % [r for r in q])

def main():
    time.tzset() # Fix SDK time bug
    application = webapp.WSGIApplication([
            ('/.*', Bop),
            ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
