import wsgiref.handlers
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from datetime import datetime, timedelta
import time
import pytz
from models import Row, Marker
import logging
import formencode
from formencode import htmlfill
from google.appengine.api import users
import cgi

type_list = [
    'feed','poop','bath','vitimins','meds','litter','daddychow'
]

log = logging.getLogger(__name__)


class Type(db.Model):
    name = db.StringProperty()
    def __repr__(self):
        return 'Type(%s)'%self.name

class Event(db.Expando):
    create_time = db.DateTimeProperty()
    event_time = db.DateTimeProperty()
    type = db.ReferenceProperty(Type)
    def __repr__(self):
        return 'Event(%s: %s)'%(self.type.name, self.event_time)

class IndexPage(webapp.RequestHandler):
    def get(self):
        log.error('pop')
        self.redirect('/mini')
#        self.response.out.write(template.render('templates/pre.html', {
#            'text': 'index'}))

class Hello(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render('templates/pre.html', {
            'text': 'hello\n'}))

class Init(webapp.RequestHandler):
    def get(self):
        for type_name in type_list:
            q = Type.all().filter('name =', type_name)
            x = q.fetch(1)
            if len(x) == 0:
                t = Type(name=type_name)
                t.put()
        self.response.out.write(template.render('templates/pre.html', {
            'text': 'init'}))

class EventsHandler(webapp.RequestHandler):
    def get(self, format):
        self.response.out.write(template.render('templates/pre.html', {
            'text': 'qwer'}))
    def post(self, format):
        type_name = self.request.get('type')
        type = Type.all().filter('name =', type_name).fetch(1)[0]
        create_time = datetime.now()
        #event_time = self.request.get('event_time', create_time)
        event_time = datetime.strptime(
                self.request.get('event_time'),'%Y-%m-%d %H:%M:%S+00:00'
            ).replace(tzinfo=pytz.utc)
        new = Event(type=type, create_time=create_time, event_time=event_time)
        key = new.put()
        #self.redirect('/events/%s'%key)
        self.redirect('/mini')


class EventHandler(webapp.RequestHandler):
    def get(self, key, format):
        event = db.get(key)
        text  = 'key: %s\n'%key
        text += 'format: %s\n'%format
        text += 'type: %s\n'%event.type.name
        text += 'create_time: %s\n'%event.create_time
        text += 'event_time: %s\n'%event.event_time
        self.response.out.write(template.render('templates/pre.html', {
            'text': text}))
    def put(self, key, format):
        pass
    def delete(self, key, format):
        pass

class TypeShower(webapp.RequestHandler):
    def get(self, type_name):
        type = db.GqlQuery('SELECT * FROM Type WHERE name = :name',
            name = type_name).fetch(1)[0]
        evt = db.GqlQuery('SELECT * FROM Event WHERE type = :type_key'
            ' ORDER BY event_time', type_key = type.key()).fetch(1)[0]
        self.response.out.write(template.render('templates/pre.html', {
            'text': 'asdf -%s-'%evt}))

class FormDisplay(webapp.RequestHandler):
    def get(self):
        times = []
        eastern = pytz.timezone('US/Eastern')
        for type_name in type_list:
            type = db.GqlQuery('SELECT * FROM Type WHERE name = :name',
                name = type_name).fetch(1)[0]
            try:
                evt = db.GqlQuery('SELECT * FROM Event WHERE type = :type_key'
                        ' ORDER BY event_time DESC',type_key = type.key()
                    ).fetch(1)[0]
                t = evt.event_time.replace(tzinfo=pytz.utc
                    ).astimezone(eastern).strftime('%I:%M %p [%a]')
                #t += evt.event_time.tzinfo
            except IndexError:
                t = 'None'
            times.append({'name':type_name, 'time':t})

        now = datetime.utcnow().replace(tzinfo=pytz.utc,second=0,microsecond=0)
        adj_min = now.minute % 10
        if adj_min >= 5:
            adj_now = now + timedelta(minutes=(10-adj_min))
        else:
            adj_now = now - timedelta(minutes=adj_min)

        dt_lst1 = [adj_now+timedelta(minutes = x*10) for x in range(-16, -1)]
        dt_lst2 = [adj_now+timedelta(minutes=x*10) for x in range(1, 16)]

        options = '\n'.join([
            '<option value="%s">%s</option>'%(
                dt,dt.astimezone(eastern).strftime('%I:%M')
            ) for dt in dt_lst1])

        options += '\n<option selected value="%s">%s</option>\n'%(
                adj_now,adj_now.astimezone(eastern).strftime('%I:%M')
            )

        options += '\n'.join([
            '<option value="%s">%s</option>'%(
                dt,dt.astimezone(eastern).strftime('%I:%M')
            ) for dt in dt_lst2])

        self.response.out.write(template.render('templates/mini.html',
            {'type_list': type_list, 'times': times, 'options': options}))

def main():
    time.tzset() # Fix SDK time bug
    application = webapp.WSGIApplication([
                ('/', IndexPage),
                ('/hello', Hello),
                ('/init', Init),
                ('/mini', FormDisplay),
                ('/events(?:\.([^/]+))?',EventsHandler),
                ('/events/([^/]+?)(?:\.([^/]+))?',EventHandler),
                ('/types/(.*)/show', TypeShower),
            ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()

