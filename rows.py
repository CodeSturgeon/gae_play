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

#log = logging.getLogger().setLevel(logging.DEBUG)

class RowEdit(formencode.Schema):
    row_key = formencode.validators.String()
    row_name = formencode.validators.String(not_empty=True)
    submit = formencode.validators.String(not_empty=True)

class IndexPage(webapp.RequestHandler):
    def get(self):
        rows = db.Query(Row)
        text = []
        for row in rows:
            text.append('%s %s' % (row.key(), row.owner))
            for marker in Marker.all().filter("row =", row):
                text.append(' - %s %s' % (marker.time, marker.value))
        text.append(str(self.request.environ))
        text = '\n'.join(text)
        self.response.out.write(template.render('templates/pre.html', {
            'text': text}))

def make_template_rows(segments, rows):
    template_rows = []
    for row in rows:
        row_dict = {}
        row_dict['name'] = '-%s-' % row.name
        row_dict['key'] = row.key()
        row_dict['segments'] = []
        
        start = segments[-1:][0]['time_start']
        end = segments[0]['time_end']
#        text += 'Start: %s\n' % start
#        text += 'End: %s\n' % end

        markers_query = db.Query(Marker)
        markers_query.filter('row =', row)
        markers_query.filter('time >=', start)
        markers_query.filter('time <', end)
        markers_query.order('-time')

        markers = markers_query.fetch(1000)
        logging.info('Markers: %s' % markers)
        for segment in segments:
            d = {}
            if markers != [] and \
                    markers[0].time >= segment['time_start']:
                local_markers = []
                while markers[0].time >= segment['time_start']:
                    local_markers.append(markers.pop(0))
                    if markers == []:
                        break
#                d['value'] = len(local_markers)
                d['value'] = sum([m.value for m in local_markers])
                d['href'] = '/del?%s' % '&'.join([
                    'marker=%s' % m.key() for m in local_markers])
            else:
                d['value'] = 0
                d['href'] = '/add?row_key=%s&timestamp=%d' % (row.key(),
                    time.mktime(segment['time_start'].timetuple()))
            row_dict['segments'].append(d)
        if markers != []:
            log.error('Markers left over! %s' % markers)
        template_rows.append(row_dict)
    return template_rows

def make_segments(now, number):
    segments = []
    for lop in range(number):
        segment = {}
        segment['name'] = '-%d' % (lop + 1)
        segment['time_end'] = now - datetime.timedelta(days = lop)
        segment['time_start'] = now - datetime.timedelta(days = lop + 1)
        segment['title'] = 'Start: %s\nEnd: %s' % (segment['time_start'],
            segment['time_end'])
        segments.append(segment)
    return segments

class EditLine(webapp.RequestHandler):
    def get(self):
        key = self.request.params.get('key')
        name = ''
        if key:
            row = db.get(key)
            name = row.name
        html_form = (template.render('templates/row_edit.html', {'key': key}))
        defaults = {'row_name': name, 'row_key': key}
        self.response.out.write(htmlfill.render(html_form, defaults))

    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url("/"))
            return
        schema = RowEdit()
        try:
            form_result = schema.to_python(self.request.params)
        except formencode.validators.Invalid, e:
            self.response.out.write(e)
            return
        
        if form_result.get('row_key') != '':
            row = db.get(form_result.get('row_key'))
            # FIXME put user check in here
            row.name = form_result.get('row_name')
            row.put()
        else:
            row = Row(name = form_result.get('row_name'), owner = user)
            row.put()

        self.redirect('/show')

class ShowLines(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            user_name = user.nickname()
            user_url = users.create_logout_url("/")
        else:
            self.redirect(users.create_login_url("/"))
            return
        now = datetime.datetime.now()
        now = now.replace(hour = 0, minute = 0,
            second = 0, microsecond = 0)
        rows = []
        rows = Row.all().filter("owner =",user)
        text = 'Now: %s\n' % now
        text += 'User: %s, URL: %s\n' % (user_name, user_url)

        segments = make_segments(now, 15)

        template_rows = make_template_rows(segments, rows)

        self.response.out.write(template.render('templates/lines.html',
                {'text': text, 'segments': segments,
                'template_rows': template_rows, 'user_name': user_name,
                'user_url': user_url}))

class AddMarker(webapp.RequestHandler):
    def get(self):
        timestamps = self.request.params.getall('timestamp')
        row = self.request.params.get('row_key')
        for timestamp in timestamps:
            t = datetime.datetime.fromtimestamp(float(timestamp))
            r = db.get(row)
            m = Marker(time = t, row = r, value = 3)
            m.put()
        referer = self.request.environ.get('HTTP_REFERER')
        if referer:
            self.redirect(referer)
        else:
            show = '/show?key=%s' % row.key()
            self.redirect(show)

class DelMarker(webapp.RequestHandler):
    def get(self):
        markers = self.request.params.getall('marker')
        markers = db.get(markers)
        for marker in markers:
            row_key = marker.row
            db.delete(marker)
        referer = self.request.environ.get('HTTP_REFERER')
        if referer:
            self.redirect(referer)
        else:
            show = '/show?key=%s' % row_key
            self.redirect(show)

class MakeRow(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            user_name = user.nickname()
            user_url = users.create_logout_url("/")
        else:
            self.redirect(users.create_login_url("/"))
            return
        r = Row(name = 'NewRow', owner = user)
        r.put()
        self.redirect('/show')

def main():
    time.tzset() # Fix SDK time bug
    application = webapp.WSGIApplication([
            ('/', IndexPage),
            ('/init', MakeRow),
            ('/show', ShowLines),
            ('/add', AddMarker),
            ('/del', DelMarker),
            ('/edit', EditLine)
            ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
