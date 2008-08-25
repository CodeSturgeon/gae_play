import wsgiref.handlers
from google.appengine.ext import webapp, db
import logging

class Amphibian(db.Expando):
    color = db.StringProperty()
    weight = db.FloatProperty()

class Frog(Amphibian):
    spawn = db.IntegerProperty()

class TestEntity(db.Expando):
    str = db.StringProperty()

class TestPage(webapp.RequestHandler):
    def get(self, flip='flip_default', flop='flop_default'):
        logging.info('TestPage [%s]{%s}'%(flip,flop))

application = webapp.WSGIApplication([('(?P<flop>.*)', TestPage)],
    debug=True)
wsgiref.handlers.CGIHandler().run(application)

