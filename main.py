from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template

from foursquare import *
from google.appengine.api import urlfetch
import logging  
import keys

from django.utils import simplejson as json 
from gaesessions import get_current_session

helper = FoursquareAuthHelper(keys.foursquare_client, keys.foursquare_secret, keys.foursquare_callback)

class User(db.Model):
  access_token  = db.StringProperty(required=False)
  foursquare_id = db.StringProperty(required=False)
  first_name    = db.StringProperty(required=False)
  last_name     = db.StringProperty(required=False)

  @staticmethod
  def get_or_create_user_by_foursquare_id(id):
    user_query = User.all().filter("foursquare_id", id).fetch(1)
    if len(user_query) == 0:
      user = User(foursquare_id=id)
      user.put()
    else:
      user = user_query[0]
    return user

class Hunt(db.Model):
  name = db.StringProperty(required=False)
  user = db.ReferenceProperty(User, collection_name='hunts')

 
class MainHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      self.redirect("/dashboard")
    else:
      self.response.out.write(template.render('templates/main.html', locals()))

class DashboardHandler(webapp.RequestHandler):
  def get(self): 
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      hunts = user.hunts
      self.response.out.write(template.render('templates/dashboard.html', locals()))
    else:
      self.redirect("/")

class LoginHandler(webapp.RequestHandler):
  def get(self):
    self.redirect(helper.get_authentication_url())

class LogoutHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    self.redirect('/')

class OAuthCallbackHandler(webapp.RequestHandler):
  def get(self):
    code = self.request.get("code")                                           
    token_url = helper.get_access_token_url(code)
    result = urlfetch.fetch(token_url)                                        
    result = json.loads(result.content)

    client = FoursquareClient(result["access_token"])                         
    user_info = client.users()
    user = User.get_or_create_user_by_foursquare_id(user_info["response"]["user"]["id"])
    user.first_name = user_info["response"]["user"]["firstName"]
    user.last_name  = user_info["response"]["user"]["lastName"]
    user.access_token = result["access_token"] 
    user.put()

    session = get_current_session()
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    session['user'] = user 
    self.redirect('/dashboard')

class HuntCreateHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      self.response.out.write(template.render('templates/hunt-create.html', locals()))
    else:
      self.redirect("/")
 
  def post(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      name = self.request.get("name")
      hunt = Hunt(name=name,user=user)
      hunt.put()
      self.redirect("/dashboard")
    else:
      self.redirect("/")
 
def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/dashboard', DashboardHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/oauth_callback', OAuthCallbackHandler),
    ('/hunt/create', HuntCreateHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
