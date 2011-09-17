from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template

from foursquare import *
from google.appengine.api import urlfetch
import logging  
import keys

from django.utils import simplejson as json 
from gaesessions import get_current_session

helper = FoursquareAuthHelper(keys.foursquare_client, keys.foursquare_secret, keys.foursquare_callback)

class MainHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/main.html', locals()))

class DashboardHandler(webapp.RequestHandler):
  def get(self): 
    session = get_current_session()
    if session.has_key('access_token'):
      access_token = session['access_token']
    self.response.out.write(template.render('templates/dashboard.html', locals()))

class LoginHandler(webapp.RequestHandler):
  def get(self):
    self.redirect(helper.get_authentication_url())

class OAuthCallbackHandler(webapp.RequestHandler):
  def get(self):
    code = self.request.get("code")                                           
    token_url = helper.get_access_token_url(code)
    result = urlfetch.fetch(token_url)                                        
    result = json.loads(result.content)

    session = get_current_session()
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    session['access_token'] =  result["access_token"]


    #### TODO: LOG THE USER IN(OUR SESSION)
    #### TODO: IF THE USER DOESN'T EXIST, STORE IN THE DB
    #### TODO: IF IT DOES EXIST, WE UPDATE THE ACCESS TOKEN
    #client = FoursquareClient(result["access_token"])                         
    #lol = client.users_venuehistory()

    self.redirect('/dashboard')

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/dashboard', DashboardHandler),
    ('/login', LoginHandler),
    ('/oauth_callback', OAuthCallbackHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
