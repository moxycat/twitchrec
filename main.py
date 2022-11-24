import streamlink as sl
from streamlink.plugins import twitch
import requests as r
import json, time, pytz, iso8601, sys
from datetime import datetime
from subprocess import Popen
import config

def get_token():
    resp = r.post(
        "https://id.twitch.tv/oauth2/token",
        headers={"Content-type": "application/x-www-form-urlencoded"},
        data="client_id=%s&client_secret=%s&grant_type=client_credentials" % (config.id, config.secret)
    )
    d:dict = json.loads(resp.text)
    if "access_token" not in d.keys() or "expires_in" not in d.keys() or "token_type" not in d.keys():
        raise Exception("Returned data does not follow expected format.")
    config.token = d["access_token"]

def check_user(username):
    resp = r.get(
    "https://api.twitch.tv/helix/streams?user_login=%s" % (username,),
    headers={
        "Authorization": "Bearer %s" % (config.token,),
        "Client-Id": config.id
    })
    d = resp.json()
    if d is None or not d["data"]: return (False, None)
    else: return (True, d["data"][0])

def loop(username):
    recording = False
    while True:
        print(f"Checking if user {username} is online...")
        online, info = check_user(username)
        if recording and not online:
            print("User went offline. Stopping recording...")
            proc.kill()
            recording = False
            print("Cleaning up file...")
            proc = Popen("ffmpeg -hide_banner -loglevel error -stats -y -i \"%s.mkv\" -ss %d -vcodec copy -acodec copy \"%s_cut.mkv\"" % (title, junk_time, title))
            proc.wait()
        if not online:
            print("User not online. Waiting 10 minutes before next check.")
            time.sleep(30)
            continue
        if recording:
            time.sleep(60)
            continue
        stream_start: datetime = iso8601.parse_date(info["started_at"])
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        print(datetime.strftime(stream_start, "%Y-%m-%d %H:%M:%S"))
        print(datetime.strftime(now, "%Y-%m-%d %H:%M:%S"))
        junk_time = int((now - stream_start).total_seconds())
        print("User is streaming. Starting recording...")
        title = "%s_%s" % (datetime.strftime(datetime.now(), "%Y-%m-%d_%Hh%Mm%Ss"), info["user_name"])
        
        ret: dict[twitch.TwitchHLSStream] = sl.streams("https://www.twitch.tv/" + username)
        if "best" in ret.keys(): url = ret["best"].url
        else:
            # :skull:
            url = ret[list(filter(lambda x: x != "audio_only" or x != "worst", ret.keys()))[-1]].url
        print(url)
        proc = Popen("ffmpeg -hide_banner -loglevel error -stats -y -i %s -c copy -use_wallclock_as_timestamps 1 \"%s.mkv\"" % (url, title))
        print("Recording started. Writing to file \"%s\"..." % (title,))
        recording = True
        time.sleep(60)

if len(sys.argv) < 2:
    print("You need to supply a Twitch username.")
    exit(0)
else:
    get_token()
    loop(sys.argv[1])