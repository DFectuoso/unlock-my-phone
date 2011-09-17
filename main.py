from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from foursquare import *                                                      
from google.appengine.api import urlfetch
import logging  
import keys

from django.utils import simplejson as json 

helper = FoursquareAuthHelper(keys.foursquare_client, keys.foursquare_secret, "http://127.0.0.1:9119/oauth_callback")

class MainHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write('Hello world!')

class LoginHandler(webapp.RequestHandler):
  def get(self):
    self.redirect(helper.get_authentication_url())

class OAuthCallbackHandler(webapp.RequestHandler):
  def get(self):
    code = self.request.get("code")                                           
    token_url = helper.get_access_token_url(code)
    result = urlfetch.fetch(token_url)                                        
    result = json.loads(result.content)

    #### TODO: LOG THE USER IN(OUR SESSION)
    #### TODO: IF THE USER DOESN'T EXIST, STORE IN THE DB
    #### TODO: IF IT DOES EXIST, WE UPDATE THE ACCESS TOKEN
    #client = FoursquareClient(result["access_token"])                         
    #lol = client.users_venuehistory()

    self.redirect('/')


    self.response.out.write('Hello world!')

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/login', LoginHandler),
    ('/oauth_callback', OAuthCallbackHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
