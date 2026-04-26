import os
import time
import sqlite3
import requests
import datetime

import streamlit as st
import pandas as pd

import myjdapi
import short_unique_id as short_id
import human_readable

dbfile = "./forjoytv.db"

st.set_page_config(page_title="ForJoy TV", layout="wide")
                   
st.title("ForJoy TV")

if os.path.exists(dbfile):
    con = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
else:
    st.error('Database missing.')
    st.stop()

st_left, st_mid, st_right = st.columns([0.4, 0.15, 0.4], border=True)

st_left.header('Channel')
st_mid.header('Day')
st_right.header('Show')

sel_channelid = None
sel_dayid = None

with st_left:
    channels = pd.read_sql('SELECT * FROM channels;', con)
    sel_channel = st.dataframe(channels, hide_index=True, selection_mode="single-row", on_select="rerun")
    if len(sel_channel.selection.rows)==0:
        sel_channelid = None
    else:
        sel_channelid = channels.iloc[sel_channel.selection.rows[0]].id
    
with st_mid:
    if sel_channelid==None:
        st.info('Select a channel first.')
        st.stop()
    days = pd.read_sql(f'select distinct date(time) as day from shows where channel_id = {sel_channelid} order by day asc', con)
    sel_day = st.dataframe(days, hide_index=True, selection_mode="single-row", on_select="rerun", 
                           column_config={'day': st.column_config.DatetimeColumn(format="ddd, DD.MM.")})
    if len(sel_day.selection.rows)==0:
        sel_dayid = None    
    else:
        sel_dayid = days.iloc[sel_day.selection.rows[0]].day

with st_right:
    if sel_dayid==None:
        st.info('Select a day first.')
        st.stop()
    shows = pd.read_sql(f'select id, time(time) as time, date(time) as date, title, path from shows where channel_id = {sel_channelid} and date(time)="{sel_dayid}" order by time asc', con)
    sel_show = st.dataframe(shows, hide_index=True, column_order=("time", "title",), selection_mode="single-row", on_select="rerun")
    if len(sel_show.selection.rows)==0:
        sel_showid = None    
    else:
        sel_showid = shows.iloc[sel_show.selection.rows[0]].id

if sel_showid is None:
    st.stop()

st.header('Selected Show')
(_, showtime, showdate, showtitle, showpath) = cur.execute(f'select id, time(time) as time, date(time) as date, title, path from shows where id = {sel_showid}').fetchone()

st.write(f'{showdate}, {showtime}:', showtitle)
if showpath=="":
    st.info('Show is not yet recorded')
    st.stop()

filename = st.text_input('Enter File name', value=showtitle, placeholder="The name of the downloaded file")

if filename=="" or filename is None:
    st.info("Please enter a file name")
    st.stop() 

folder = st.selectbox("Download to which folder?", ("Yuzuru", "ForJoyTV"))

if not st.button("Download to Plex", type="primary"):
    st.stop()    

with st.status("Downloading ...", expanded=True) as status:
    st.write("Retrieving download URL from ForJoyTV...")
    url = f'http://live.forjoytv.com:9083{showpath}=.m3u8'
    
    r=requests.get(url, 
                   params={"type":"vod",
                           "__cross_domain_user": "b9vg1quKwlzKNX5IvrCFh+58AxxjMkF7CF5ju7Xe+vQBE6HUrXii7Q+fv4fVPHpmLf/0jIYxWZEVdO/hnZODU5JFkw0NjYL25yblm2CmdrMoWmzTB788qoywmdrKI0jvFsZd3m5lR8QAFMUMZcfSpx4cs1pdiuJi9j5YYhHy/9EqjiYG7ebbxXON8MeAbUNOiONXX3eVOffQUiv1m+pbMziokaSU2vazFtLzF+BXSDirVnhxf+5jEacNXEMltyDOcxqhkRxDEq8Z2pJQLUPFnWZTi3zrmLI9CBboQ9LuacjUy22TXyYUIpB8K8STRilxLxfQNSKeqZjHRsCevC8qIBkaMoG/sR5AWpVuSTdnX7xNELeBXCwF40GSoyh5vlCjwIm2LClPy3ISNpZA3/o+YhIgdl2WUv9+Ob0huHvQl8TgAb2r81mEWnHVBH/0teU1aGhBowbo+CxC2V2jTyAJv3k9EO8fo59zRxYFPvFZRURsIDYqaaTgZMPOLqKrCJnDxGtj/GeIFZRToput4pOnQmJ6Wdk7VH4/Kd77VXUYeUavJ1LDqLcVjy0D3sB4symarkoCWXUPWFTt3XkCN16A9J44hZBMX7sJ3i5o9bFdHw8="},
                   headers={"dnt":"1","host":"live.forjoytv.com:9083", 
                            "origin":"http://play.forjoytv.com",
                            "referer":"http://play.forjoytv.com/", "sec-gpc":"1"})
    
    
    if r.status_code!=200:
        st.error(f"Something is wrong, error code {r.status_code}")
        st.stop()
    
    st.write("Connecting to Downloader...")
    jd=myjdapi.Myjdapi()
    jd.direct_connect('jdownloader2.fritz.box', 3128, timeout=10)
    downloader = jd.get_device()
    
    st.write("Sending download URL to Downloader...")
    uid = short_id.generate_short_id()
    prefix = f'{folder}#{uid}#'
    link = downloader.linkgrabber.add_links([{
        "autostart" : False,
        "links" : r.text,
        "packageName" : f'{prefix}{filename}',
        "extractPassword" : None,
        "priority" : "DEFAULT",
        "downloadPassword" : None,
        "destinationFolder" : None
        }])
    st.write(link)
    
    st.write("Waiting for Downloader to find the file ...")

    while (True):
        linkgrabberpkgs = [pkg for pkg in downloader.linkgrabber.query_packages() if pkg['name'].startswith(prefix) ]
        if len(linkgrabberpkgs)==1:
            break
        time.sleep(1)
  
    linkgrabberpkg = linkgrabberpkgs[0]
    #st.write(linkgrabberpkg)

    if linkgrabberpkg["onlineCount"]!=1:
        st.warn(f"Linkgrabber found {linkgrabberpkg['onlineCount']} files instead of one.")
        st.stop()
  
    linkgrabberlnks = [lnk for lnk in downloader.linkgrabber.query_links() if lnk["packageUUID"]==linkgrabberpkg["uuid"]]
    if len(linkgrabberpkgs)!=1:
        st.warn(f"Linkgrabber found {len(linkgrabberlnks)} links instead of one.")
        st.write()
    linkgrabberlnk=linkgrabberlnks[0]
    
    #st.write(linkgrabberlnk)
    
    st.write("Starting the Downloader ...")
    downloader.linkgrabber.move_to_downloadlist([linkgrabberlnk["uuid"]], [linkgrabberlnk["packageUUID"]])
    time.sleep(5)
    while (True):
        downloaderlnks = [lnk for lnk in downloader.downloads.query_links() if lnk['uuid']==linkgrabberlnk['uuid'] ]
        if len(downloaderlnks)==1 and "eta" in downloaderlnks[0]:
            break
        time.sleep(1)
    downloaderlnk = downloaderlnks[0]
    eta=datetime.timedelta(seconds=int(downloaderlnk['eta']))
    st.write(f"Estimated download finished in {human_readable.time_delta(1.3*eta)}")
    
    status.update(
        label="Download has started", state="complete"
    )

st.write("Ciao")