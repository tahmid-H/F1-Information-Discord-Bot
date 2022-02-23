import os
import pandas as pd
from dateutil import tz
from pytz import country_timezones
import us
import pickle
import numpy as np
from datetime import datetime, timedelta, timezone
import requests as rq

# saves to timezoneData.pkl
def timezoneGetter():
    timezone_countries = {timezone: country 
                          for country, timezones in country_timezones.items()
                          for timezone in timezones}

    timezone_countries = dict((v,k) for k,v in timezone_countries.items())
    usDict = {}
    for i in us.STATES:
        usDict[i.abbr] = i.capital_tz
    timezone_countries['US'] = usDict
    with open('timezoneData.pkl', 'wb') as handle:
        pickle.dump(timezone_countries, handle, protocol=pickle.HIGHEST_PROTOCOL)

# saves F1 schedule formatted to UTC time to timezoneData.pkl
def f1ScheduleFormatter():
    df = pd.read_json("./backend/schedule.json")
    df['round_old'] = df['round']
    df['round'] = df.apply(lambda x: x['round_old'] - 2, axis=1)
    df = df.drop([0,1]).drop(columns=['round_old', 'format', 'meetingStartDate']).set_index('round').replace('TBC', None)
    
    # gets GMT offset
    headers = {"authority": "api.formula1.com","method": "GET","path": "/v1/event-tracker","scheme": "https","accept": "application/json, text/javascript, */*; q=0.01","accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9","apikey": "qPgPPRJyGCIPxFT3el4MF7thXHyJCzAP","locale": "en","origin": "https://www.formula1.com","referer": "https://www.formula1.com/","sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows","sec-fetch-dest": "empty","sec-fetch-mode": "cors","sec-fetch-site": "same-site","user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
    res = rq.get("https://api.formula1.com/v1/editorial-eventlisting/events", headers=headers).json()['events']
    dfTz = pd.DataFrame(res)
    dfTz = dfTz[['meetingOfficialName', 'gmtOffset']].drop([0,1]).reset_index(drop=True).set_index('meetingOfficialName')
    df['gmtOffset'] = df.apply(lambda x: dfTz.at[x['meetingOfficialName'],'gmtOffset'], axis=1)

    # changing time str to datetime object
    for i in range(1, 6):
        df['newSession' + str(i) + 'Date'] = df.apply(lambda x: None if x['session' + str(i) + 'Date'] is None else datetime.strptime(str(x['session' + str(i) + 'Date']) + str(x['gmtOffset']), "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc).isoformat(), axis=1)

    #dropping old times
    df.drop(columns=['session1Date', 'session2Date', 'session3Date', 'session4Date', 'session5Date'], inplace=True)
    df.rename(columns={'newSession1Date': 'session1Date', 'newSession2Date': 'session2Date', 'newSession3Date': 'session3Date', 'newSession4Date': 'session4Date', 'newSession5Date': 'session5Date'}, inplace=True)
    df.to_pickle('./backend/raceSchedule.pkl')

f1ScheduleFormatter()