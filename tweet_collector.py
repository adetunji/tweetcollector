# Author: Tunji Akinbami
import sys
import time

from twython import Twython, TwythonError
from py2neo import Graph, Relationship, authenticate

# Requires Authentication as of Twitter API v1.1
APP_KEY = ''
APP_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''
twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

# Neo4j auth
NEO4J_USERNAME = 'NEO4J_USERNAME'
NEO4J_PASSWORD = 'NEO4J_PASSWORD'

if NEO4J_USERNAME and NEO4J_PASSWORD:
    authenticate('localhost:7474', NEO4J_USERNAME, NEO4J_PASSWORD)

graph = Graph()

# Twitter auth

def find_tweets(keyword, since_id):
    try:
        search_results = twitter.search(q=keyword, count=50)
    except TwythonError as e:
        print e

    tweets = search_results['statuses']
    return tweets


def upload_tweets(tweets):
    for t in tweets:
        u = t['user']
        e = t['entities']

        tweet = graph.merge_one("Tweet", "id", t['id'])
        tweet.properties['text'] = t['text']
        tweet.push()

        user = graph.merge_one("User", "username", u['screen_name'])
        graph.create_unique(Relationship(user, "POSTS", tweet))

        for h in e.get('hashtags', []):
            hashtag = graph.merge_one("Hashtag", "name", h['text'].lower())
            graph.create_unique(Relationship(hashtag, "TAGS", tweet))

        for m in e.get('user_mentions', []):
            mention = graph.merge_one("User", "username", m['screen_name'])
            graph.create_unique(Relationship(tweet, "MENTIONS", mention))

        reply = t.get('in_reply_to_status_id')
        if reply:
            reply_tweet = graph.merge_one("Tweet", "id", reply)
            graph.create_unique(Relationship(tweet, "REPLY_TO", reply_tweet))

        r = t.get('retweeted_status', {})
        r = r.get('id')

        if r:
            retweet = graph.merge_one("Tweet", "id", r)
            graph.create_unique(Relationship(tweet, "RETWEETS", retweet))


def constraint(label, property):
    if property not in graph.schema.get_uniqueness_constraints(label):
        graph.schema.create_uniqueness_constraint(label, property)


constraint("Tweet", "id")
constraint("User", "username")
constraint("Hashtag", "name")

since_id = -1

while True:
    try:
        tweets = find_tweets(sys.argv[1], since_id=since_id)

        if not tweets:
            print("No tweets found.")
            time.sleep(60)
            continue

        since_id = tweets[0].get('id')
        upload_tweets(tweets)

        print(str(len(tweets)) + " tweets uploaded!")
        time.sleep(60)

    except Exception as e:
        print(e)
        time.sleep(60)
        continue


