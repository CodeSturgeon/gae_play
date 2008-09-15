import wsgiref.handlers
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from datetime import datetime, timedelta
import time
import pytz
from models import Row, Marker
import logging
import formencode
from formencode import htmlfill, validators
from google.appengine.api import users
import cgi

from jsonprop import JSONProperty

type_list = [
    'feed','poop','bath','vitimins','meds','wardrobe','litter','daddychow'
]

log = logging.getLogger(__name__)


class Type(db.Model):
    name = db.StringProperty()
    data_defs = JSONProperty()
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
        text = ''
        for type_name in type_list:
            q = Type.all().filter('name =', type_name)
            x = q.fetch(1)
            if len(x) == 0:
                t = Type(name=type_name)
                text += 'make %s\n'%type_name
            else:
                t = x[0]
                text += 'find %s\n'%type_name

            if t.name in ['feed']:
                t.data_defs = [{'name':'amount', 'validator':'Int'}]
                text += 'def %s\n'%type_name
            elif t.name in ['poop']:
                t.data_defs = [{'name':'size', 'validator':'OneOf',
                    'vinit_a':[['small', 'medium', 'large']],
                    'vinit_d':{'not_empty':'1'},
                    }]

            t.put()

        self.response.out.write(template.render('templates/pre.html', {
            'text': text}))

class EventsHandler(webapp.RequestHandler):
    def get(self, format):
        self.response.out.write(template.render('templates/pre.html', {
            'text': 'qwer'}))
    def post(self, format):
        type_name = self.request.get('type')
        d = {}
        t = Type.all().filter('name =', type_name).fetch(1)[0]
        d['type'] = t
        d['create_time'] = datetime.now()
        d['event_time'] = datetime.strptime(
                self.request.get('event_time'),'%Y-%m-%d %H:%M:%S+00:00'
            ).replace(tzinfo=pytz.utc)
        if type(t.data_defs) is list:
            log.error('doing validation')
            data = self.request.get('data',None)
            validator_f = getattr(validators, t.data_defs[0]['validator'])
            validator_a = t.data_defs[0].get('vinit_a', [])
            # Convert unicode keys to plain strings
            validator_d_uni = t.data_defs[0].get('vinit_d', {})
            validator_d = {}
            for (key, value) in validator_d_uni.iteritems():
                validator_d[str(key)] = value
            # Create validator
            validator = validator_f(*validator_a, **validator_d)
            try:
                vdata = validator.to_python(data)
                d[str(t.data_defs[0]['name'])] = vdata
            except formencode.Invalid, e:
                self.response.out.write(template.render('templates/pre.html', {
                    'text': e}))
                return
        new = Event(**d)
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
        now = datetime.utcnow().replace(tzinfo=pytz.utc,second=0,microsecond=0)
        eastern = pytz.timezone('US/Eastern')

        # Compile times for types
        times = []
        for type_name in type_list:
            type = db.GqlQuery('SELECT * FROM Type WHERE name = :name',
                name = type_name).fetch(1)[0]
            try:
                events = db.GqlQuery('SELECT * FROM Event WHERE type = :type_key'
                        ' ORDER BY event_time DESC',type_key = type.key()
                    ).fetch(2)
                t1 = events[0].event_time.replace(tzinfo=pytz.utc
                    ).astimezone(eastern).strftime('%I:%M %p [%a]')
                #t += evt.event_time.tzinfo
            except IndexError:
                t1 = 'None'

            try:
                t2 = events[1].event_time.replace(tzinfo=pytz.utc
                    ).astimezone(eastern).strftime('%I:%M %p [%a]')
                #t += evt.event_time.tzinfo
            except IndexError:
                t2 = 'None'

            times.append({'name':type_name, 'time1':t1, 'time2':t2})


        # Make time selector
        adj_min = now.minute % 10
        if adj_min >= 5:
            adj_now = now + timedelta(minutes=(10-adj_min))
        else:
            adj_now = now - timedelta(minutes=adj_min)

        dt_lst1 = [adj_now+timedelta(minutes = x*10) for x in range(-16, 0)]
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

