from google.appengine.ext import webapp, db
import datetime

class Row(db.Model):
    name = db.StringProperty()
    owner = db.UserProperty()

class Marker(db.Model):
    time = db.DateTimeProperty()
    row = db.ReferenceProperty(Row, collection_name = 'markers')
    value = db.IntegerProperty()

    def __repr__(self):
        return str(self.time)

#    def __add__(self, other):
#        return self.value + other.value
#
#    def __int__(self):
#        return self.value
#
#    def __pos__(self):
#        return self.value
