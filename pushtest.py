import urllib, urllib2
import json

def postData(url):
    checkinData = json.dumps( { "id": "4e6fe1404b90c00032eeac34",
            "createdAt": 1315955008,
            "type": "checkin",
            "timeZone": "America/New_York",
            "user": {
                "id": "13649491",
                "firstName": "Jimmy",
                "lastName": "Foursquare",
                "photo": "https://foursquare.com/img/blank_boy.png",
                "gender": "male",
                "homeCity": "New York, NY",
                "relationship": "self" },
            "venue": {
                "id": "4bda14022a3a0f47fea8a9b6",
                "name": "foursquare HQ",
                "contact": { "twitter": "foursquare" },
                "location": {
                    "address": "East Village",
                    "lat": 40.72809214560253,
                    "lng": -73.99112284183502,
                    "city": "New York",
                    "state": "NY",
                    "postalCode": "10003",
                    "country": "USA"
                    },
                "categories": [
                    {
                        "id": "4bf58dd8d48988d125941735",
                        "name": "Tech Startup",
                        "pluralName": "Tech Startups",
                        "shortName": "Tech Startup",
                        "icon": "https://foursquare.com/img/categories/building/default.png",
                        "parents": [ "Professional & Other Places", "Offices" ],
                        "primary":True
                    } ],
                "verified":True,
                "stats": { "checkinsCount": 7313, "usersCount": 565, "tipCount": 128 },
                "url": "http://foursquare.com" } })
    checkin = { 'checkin': checkinData}

    pData = urllib.urlencode(checkin)
    req = urllib2.Request(url, pData)
    print urllib2.urlopen(req).read()

postData('http://localhost:9119/push_api')
