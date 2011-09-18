from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template

from foursquare import *
from google.appengine.api import urlfetch
import logging
import keys
from twilio_helper import alertAllPlayers, alertAllPlayersButMe, alertPlayer

from django.utils import simplejson as json
from gaesessions import get_current_session

helper = FoursquareAuthHelper(keys.foursquare_client, keys.foursquare_secret, keys.foursquare_callback)

class User(db.Model):
  access_token  = db.StringProperty(required=False)
  foursquare_id = db.StringProperty(required=False)
  first_name    = db.StringProperty(required=False)
  last_name     = db.StringProperty(required=False)
  phone_number  = db.PhoneNumberProperty(required=False)
  created = db.DateTimeProperty(auto_now_add=True)

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
  created = db.DateTimeProperty(auto_now_add=True)

class HuntVenue(db.Model):
  foursquare_id = db.StringProperty(required=False)
  name = db.StringProperty(required=False)
  json = db.TextProperty(required=False)
  hunt = db.ReferenceProperty(Hunt, collection_name="venues")
  difficulty = db.IntegerProperty(default=1)

  @staticmethod
  def get_or_create_by_foursquare_id_and_hunt(foursquare_id, hunt):
    venue_query = HuntVenue.all().filter("foursquare_id", foursquare_id).filter("hunt",hunt).fetch(1)
    if len(venue_query) == 0:
      venue = HuntVenue(foursquare_id=foursquare_id,hunt=hunt)
      venue.put()
    else:
      venue = venue_query[0]
    return venue

  def update_info(self,venue_info):
    self.json = json.dumps(venue_info["response"]["venue"])
    self.name = venue_info["response"]["venue"]["name"]
    self.id = venue_info["response"]["venue"]["id"]
    self.put()

class HuntPlayer(db.Model):
  user            = db.ReferenceProperty(User, collection_name="playing_hunts")
  hunt            = db.ReferenceProperty(Hunt, collection_name="players")
  started_playing = db.DateTimeProperty(auto_now_add=True)

class HuntCheckin(db.Model):
  foursquare_id = db.StringProperty(required=False)
  hunt          = db.ReferenceProperty(Hunt, collection_name="checkins")
  venue         = db.ReferenceProperty(HuntVenue, collection_name="checkins")
  player        = db.ReferenceProperty(HuntPlayer, collection_name="checkins")

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
    hunt_key = self.request.get("hunt_key")
    if len(hunt_key) > 0:
      session = get_current_session()
      session["login_redirect_to_hunt"] = hunt_key
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
    logging.info(token_url)
    result = urlfetch.fetch(token_url)
    result = json.loads(result.content)

    client = FoursquareClient(result["access_token"])
    user_info = client.users()
    user = User.get_or_create_user_by_foursquare_id(user_info["response"]["user"]["id"])
    user.first_name = user_info["response"]["user"]["firstName"]
    user.last_name  = user_info["response"]["user"]["lastName"]
    user.phone_number = db.PhoneNumber(user_info["response"]["user"]["contact"]["phone"])
    user.access_token = result["access_token"]
    user.put()

    session = get_current_session()
    hunt_to_redirect = ""
    if session.has_key('login_redirect_to_hunt'):
      hunt_to_redirect = session["login_redirect_to_hunt"]

    if session.is_active():
      session.terminate()
    session.regenerate_id()
    session['user'] = user

    if hunt_to_redirect is not "":
      self.redirect('/' + hunt_to_redirect + "/join")
    else:
      self.redirect('/dashboard')

class PushApiHandler(webapp.RequestHandler):
  def post(self):
    checkin_info = json.loads(self.request.get("checkin"))
    user_id      = checkin_info["user"]["id"]
    venue_id     = checkin_info["venue"]["id"]

    # get user and venue, if we don't have a valid one, we don't care about this check in
    user = User.all().filter("foursquare_id", user_id).fetch(1)
    # Safeguard 
    if len(user) == 0:
      return
    user = user[0]

    for player in user.playing_hunts:
      # TODO, check if the hunt is active
      venue = HuntVenue.all().filter("foursquare_id", venue_id).filter("hunt", player.hunt).fetch(1)

      if len(venue) == 1:
        venue = venue[0]
        # We need to make sure the user has not been on this location before
        hunt = player.hunt
        hunt_checkin = HuntCheckin.all().filter("player", player).filter("hunt", hunt).filter("venue", venue).fetch(1)

        if len(hunt_checkin) == 0:
          hunt_checkin = HuntCheckin(player = player, hunt = hunt, venue=venue)
          # TODO add some metadata from foursquare
          hunt_checkin.put()

          points_word = "point"
          if hunt_checkin.venue.difficulty > 1:
            points_word = "points"
          alertPlayer(player, "You found a checkpoint worth " + str(hunt_checkin.venue.difficulty) + " " + points_word + "! On to the next one! Hurry!")
          alertAllPlayersButMe(player, hunt, player.user.first_name + " just found a checkpoint! Better get movin'!")
          logging.info("We are in, lets do yea and yea")
        else:
          logging.info("We had already done this thing")
      else:
        logging.info("We got a user, but the venue is not intersting for us")

class HuntCreateHandler(webapp.RequestHandler):
  def post(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      name = self.request.get("name")
      hunt = Hunt(name=name,user=user)
      hunt.put()
      self.redirect("/hunt/" + str(hunt.key()))
    else:
      self.redirect("/")

class HuntHomeHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      hunt = db.get(hunt_key)
      venues = hunt.venues
      self.response.out.write(template.render("templates/hunt-home.html",locals()))
    else:
      self.redirect("/")

class HuntChangeTimeConfigHandler(webapp.RequestHandler):
  def get(self,hunt_key):
      self.redirect("/")

class HuntAddVenueHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    session = get_current_session()
    if session.has_key('user'):
      #get user, hunt and venue_id
      user = session["user"]
      hunt = db.get(hunt_key)
      venue_id = self.request.get("venue_id")
      # get venue
      venue = HuntVenue.get_or_create_by_foursquare_id_and_hunt(venue_id,hunt)

      # update venue
      client = FoursquareClient(user.access_token)
      venue.update_info(client.venues(venue_id))
      self.response.out.write("Ok")
    else:
      self.response.out.write("Error")

class HuntRemoveVenueHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    session = get_current_session()
    if session.has_key('user'):
      #get user, hunt and venue_id
      user = session["user"]
      hunt = db.get(hunt_key)
      venue_id = self.request.get("venue_id")
      # get venue
      venue = HuntVenue.get_or_create_by_foursquare_id_and_hunt(venue_id,hunt)
      venue.delete()
      self.response.out.write("Ok")
    else:
      self.response.out.write("Error")

class HuntChangeVenueWeightHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    session = get_current_session()
    if session.has_key('user'):
      difficulty = self.request.get("difficulty")
      try:
        difficulty = max(1, min(int(self.request.get("difficulty")),3))
      except ValueError:
        return

      #get user, hunt and venue_id
      user = session["user"]
      hunt = db.get(hunt_key)
      venue_id = self.request.get("venue_id")
      # get venue
      venue = HuntVenue.get_or_create_by_foursquare_id_and_hunt(venue_id,hunt) 
      venue.difficulty = difficulty
      venue.put()
      self.response.out.write("Ok")
    else:
      self.response.out.write("Error")

class VenueSearchHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      ll = self.request.get("ll")
      ll_act = self.request.get("ll_acc")
      alt = self.request.get("alt")
      alt_acc = self.request.get("alt_acc")
      query = self.request.get("query")
      user = session["user"]
      client = FoursquareClient(user.access_token)
      self.response.out.write(json.dumps(client.venues_search(ll,ll_act,alt,alt_acc,query)))
    else:
      self.response.out.write("Error")

class HuntPlayerHomeHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    hunt = db.get(hunt_key)
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      hunt_player = HuntPlayer.all().filter("user", user).filter("hunt", hunt).fetch(1)
      if len(hunt_player) == 0:
        self.response.out.write(template.render('templates/hunt-player-join-now.html', locals()))
      else:
        hunt_player = hunt_player[0]
        venues = hunt_player.hunt.venues
        venues_for_display = []
        checkins = HuntCheckin.all().filter("player", hunt_player).fetch(1000)
        for venue in venues:
          data = (venue.name, False)
          for checkin in checkins:
            if str(venue.key()) == str(checkin.venue.key()):
              data = (venue.name, True)

          venues_for_display.append(data)

        self.response.out.write(template.render('templates/hunt-player-status.html', locals()))
      # Did he join already?
    else:
      self.response.out.write(template.render('templates/hunt-player-join-now.html', locals()))

class HuntPlayerJoinHandler(webapp.RequestHandler):
  def get(self,hunt_key):
    hunt = db.get(hunt_key)
    session = get_current_session()
    if session.has_key('user'):
      user = session["user"]
      hunt_player = HuntPlayer.all().filter("user",user).filter("hunt",hunt).fetch(1)
      if len(hunt_player) == 0:
        hunt_player = HuntPlayer(user=user,hunt=hunt)
        hunt_player.put()
        alertPlayer(hunt_player, "Thanks for joining the hunt. Good luck!")
        alertAllPlayersButMe(hunt_player, hunt, hunt_player.user.first_name + " just joined the hunt!")
      self.redirect("/" + hunt_key)
    else:
      self.redirect("/login?hunt_key="+hunt_key)

class HuntAddPhoneHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/hunt-player-add-phone.html', locals()))

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    
    ('/add-phone', HuntAddPhoneHandler),
    
    ('/dashboard', DashboardHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/oauth_callback', OAuthCallbackHandler),
    ('/push_api', PushApiHandler),
    ('/hunt/create', HuntCreateHandler),
    ('/hunt/(.+)/add_venue', HuntAddVenueHandler),
    ('/hunt/(.+)/remove_venue', HuntRemoveVenueHandler),
    ('/hunt/(.+)/change_venue_difficulty', HuntChangeVenueWeightHandler),
    ('/hunt/(.+)/set_start_end_time', HuntChangeTimeConfigHandler),
    ('/hunt/(.+)', HuntHomeHandler),
    ('/venue/search', VenueSearchHandler),
    ('/(.+)/join', HuntPlayerJoinHandler),
    ('/(.+)', HuntPlayerHomeHandler),

  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
