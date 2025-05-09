from datetime import datetime
import json
import requests
import os

import sqlite3

dbfile = "./forjoytv.db"

if os.path.exists(dbfile): os.remove(dbfile)

con = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
cur = con.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY, key NOT NULL, value);')
# cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_meta_key ON meta (key);')
cur.execute('CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY, name, description);')
# cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_channels_key ON channel (name, description);')
cur.execute('CREATE TABLE IF NOT EXISTS shows (id INTEGER PRIMARY KEY, channel_id, time timestamp, title, path, FOREIGN KEY (channel_id) REFERENCES channels (id));')

r=requests.get('http://live.forjoytv.com:9083/api', params={
    'action': 'listLives',
    'cid': '268425F12FFF3187F919B67B8DC9D5F1',
    'uid': 'C2D9261F3D5753E74E97EB28FE2D8B26',
    'referer': 'http://play.forjoytv.com',
    'type': 'video',
    'details': '1',
    'page_size': '200',
    'sort': 'no asc',
    })

print('Status:', r.status_code)
epg = json.loads(r.text)
for (key, value) in [(x, epg[x]) for x in epg if x!= 'result' and x!='parents']:
    print(key, value)
    cur.execute('REPLACE INTO meta (key, value) VALUES(?, ?)', (key, value))

print('Channels:', len(epg['result']))
for n, channel in enumerate(epg['result']):
    channel_id = n+1
    cur.execute('REPLACE INTO channels (id, name, description) VALUES(?, ?, ?)', (channel_id, channel['name'], channel.get('description', '')))
    channel_epg = json.loads(channel['record_epg'])
    print(channel_id, channel['name'], channel.get('description', ''), len(channel_epg), 'shows')
    for show in channel_epg:
        cur.execute('REPLACE INTO shows (time, title, path, channel_id) VALUES(?, ?, ?, ?)', 
                    (datetime.fromtimestamp(show['time']), show['title'], show['path'], channel_id))

con.commit()
con.close()
