import urllib, urllib2, base64, logging, keys

def alertAllPlayers(hunt, msg):
  for player in hunt.players:
    logging.info(player.user.first_name)
    sendSMS(player.user.phone_number, msg)

# Takes a HuntPlayer
def alertAllPlayersButMe(current_player, hunt, msg):
  for player in hunt.players:
    if str(current_player.key()) != str(player.key()):
      logging.info(player.user.first_name)
      sendSMS(player.user.phone_number, msg)

def sendSMS(phone_number, msg):
  logging.info("sending an sms to a player")
  url = "https://api.twilio.com/2010-04-01/Accounts/" + keys.twilio_username + "/SMS/Messages.json"
  data = {
    'From' : "+19148275514",
    'To' : phone_number,
    'Body' : msg
  }
  username=keys.twilio_username
  password=keys.twilio_password

  request = urllib2.Request(url, urllib.urlencode(data))
  base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
  request.add_header("Authorization", "Basic %s" % base64string)
  try:
    urllib2.urlopen(request)
  except:
    # not happy with 201s being returned even though it's okay
    pass
