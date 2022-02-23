import enum
from flask_pymongo import PyMongo
from flask import Flask, jsonify, request
import fastf1 as ff1
import requests as rq
from bson.json_util import dumps
import sys
import scipy as sp
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import pycountry
import pickle
import us
import pytz


load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://tahmid-H:" + str(os.getenv('MONGODB_PASSWORD')) + "@f1-data.6ge2m.mongodb.net/botData?retryWrites=true&w=majority"
mongodb_client = PyMongo(app)
db = mongodb_client.db
ff1.Cache.enable_cache('./backend/ff1Cache')
scheduleLoc = './backend/raceSchedule.pkl'

sprintTrackNames = ['Emilia Romagna', 'Interlagos', 'Red Bull Ring']
notificationChecker = ['FP1', 'FP2', 'FP3', 'sprint', 'qualification', 'race']

@app.route('/', methods=['GET', 'POST'])
def home():
    return "Homepage bro!"

@app.route('/test/')
def test():
    params = request.args
    return {'result': db.userTimezone.find_one({ '_id' : params['user']}) is None}
# ?user=<user ID>&race=<race name>&FP1=<yes>&FP2=<yes>&FP3=<yes>&qualification=<yes>&sprint=<yes>&race=<yes>
@app.route('/addNotification/')
def addnotification():
    data = request.args
    roundNumber = str(ff1.core.get_round(2022, request.args['race']))
    weekendData = db.userData.find_one({"round": roundNumber})
    updatedData = {}

    for key in data:
        if (key in notificationChecker and weekendData[key] is not None) and (data[key] != '' and data['user'] not in weekendData[key]):
            updatedData[key] = weekendData[key]
            updatedData[key].append(data['user'])
                
    try:
        db.userData.update_one({'_id' : weekendData['_id']}, {"$set": updatedData})
    except Exception as e:
        return {'Result' : 'Notification could not be added.'}
    return {'Result' : 'Notification successfully added.'}

# ?user=<user ID>&race=<race name>&FP1=<yes>&FP2=<yes>&FP3=<yes>&qualification=<yes>&sprint=<yes>&race=<yes>
@app.route('/removeNotification/')
def removenotification():
    data = request.args
    roundNumber = str(ff1.core.get_round(2022, request.args['race']))
    weekendData = db.userData.find_one({"round": roundNumber})
    updatedData = {}

    for key in data:
        if (key in notificationChecker and weekendData[key] is not None) and (data[key] != '' and data['user'] in weekendData[key]):
            updatedData[key] = weekendData[key]
            updatedData[key].remove(data['user'])
                
    try:
        db.userData.update_one({'_id' : weekendData['_id']}, {"$set": updatedData})
    except Exception as e:
        return {'Result' : 'Notification could not be removed.'}
    return {'Result' : 'Notification successfully removed.'}

@app.route('/initRaceData/')
def initracedata():
    sprintRounds = []
    for track in sprintTrackNames:
        sprintRounds.append(ff1.core.get_round(2022, track))

    res = rq.get("https://ergast.com/api/f1/2022.json").json()
    raceTable = []
    for e in enumerate(res['MRData']['RaceTable']['Races']):
        data = e[1]
        spr_txt = 'NoSpr'
        if int(data['round']) in sprintRounds:
            spr = []
            spr_txt = 'Spr'
        weekendData = ff1.core.get_session(2022, data['raceName'])
        weekFP1 = weekendData.get_practice(1)
        weekFP2 = weekendData.get_practice(2)
        weekQuali = weekendData.get_quali()
        weekRace = weekendData.get_race()
        if weekendData.is_testing() is False and str(data['round']) == str(ff1.core.get_round(2022, data['raceName'])):
            idval = str(data['season']) + str(data['round']) + str(data['raceName']).replace(" ", "") + str(data['Circuit']['circuitName']).replace(" ", "") + spr_txt
            info = {'_id': idval, 'round': data['round'], 'raceName' : data['raceName'], 'circuitName': data['Circuit']['circuitName'], 'FP1Date': weekFP1.date,'FP1Time': weekFP1.session_start_time, 'FP2Date': weekFP2.date, 'FP2Time': weekFP2.session_start_time,'qualificationDate': weekQuali.date , 'qualificationTime': weekQuali.session_start_time, 'raceDate': weekRace.date, 'raceTime': weekRace.session_start_time}
            if spr_txt == 'Spr':
                sess = ff1.core.get_session(2022, data['raceName'], 'SQ')
                info['FP3Date'] = None
                info['FP3Time'] = None
                info['sprintDate'] = sess.date
                info['sprintTime'] = sess.session_start_time
            else:
                sess = weekendData.get_practice(3)
                info['FP3Date'] = sess.date
                info['FP3Time'] = sess.session_start_time
                info['sprintDate'] = None
                info['sprintTime'] = None 

            raceTable.append(info)
    db.raceData.insert_many(raceTable, ordered = False )
    return jsonify(raceTable)

@app.route('/initUserData/')
def inituserdata():
    sprintRounds = []
    for track in sprintTrackNames:
        sprintRounds.append(ff1.core.get_round(2022, track))

    res = rq.get("https://ergast.com/api/f1/2022.json").json()
    userTable = []

    for e in enumerate(res['MRData']['RaceTable']['Races']):
        data = e[1]
        spr = None
        fp3 = []
        spr_txt = 'NoSpr'
        if int(data['round']) in sprintRounds:
            spr = []
            fp3 = None
            spr_txt = 'Spr'
        idval = str(data['season']) + str(data['round']) + str(data['raceName']).replace(" ", "") + str( data['Circuit']['circuitName']).replace(" ", "") + spr_txt
        userTable.append({'_id':  idval, 'round': data['round'], 'raceName' : data['raceName'], 'circuitName' : data['Circuit']['circuitName'], 'FP1' : [], 'FP2': [], 'FP3': fp3, 'qualification': [], 'sprint': spr, 'race': []})
    try:
        db.userData.insert_many(userTable, ordered = False )
    except Exception as e:
        print(e, file=sys.stderr)
    return jsonify("User Race Data Updated")

@app.route('/getUserData/')
def getuserdata():
    ret = dict()
    cursor = db.userData.find()
    i = 1
    for doc in cursor:
        ret[i] = doc
        i += 1
    return jsonify(dumps(ret))

# ?user=<discord user ID>&race=<race name/keyword>
@app.route('/getRace/')
def getrace():
    params = request.args
    roundNumber = str(ff1.core.get_round(2022, params['race']))
    df = pd.read_pickle(scheduleLoc).to_dict('index')
    raceDetail = df[int(roundNumber)]
    tz = db.userTimezone.find_one({ '_id' : params['user']})

    if tz is None:
        return {'Result' : raceDetail}
    else:
        userTZ = pytz.timezone(tz['tz'])
        dateFormat = '%a %-d %b, %H:%M %p'
        for i in range(1, 6):
            if raceDetail["session" + str(i) + "Date"] is not None:
                currT = datetime.fromisoformat(raceDetail["session" + str(i) + "Date"])
                raceDetail["session" + str(i) + "Date"] = currT.astimezone(userTZ).isoformat()
        return {'Result' : raceDetail}

@app.route('/purgeRace/')
def purgerace():
    df = pd.read_pickle(scheduleLoc).to_dict('index')
    df = pd.DataFrame(df).T
    df['session5Date'] = df['session5Date'].apply(lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ'))

    dfDropped = df[df['session5Date'] > datetime.utcnow()]
    dfDropped.to_pickle(scheduleLoc)
    return {'Result' : 'Old races successfully removed.'}

########## ADD TZ TO DATABASE
# ?user=<int>&country=<country>&state=<state if US>
@app.route('/addTimeZone/')
def addtimezone():
    params = request.args
    with open('./backend/timezoneData.pkl', 'rb') as handle:
       tzData = pickle.load(handle)
    alpha_2 = pycountry.countries.search_fuzzy(params['country'])[0].alpha_2
    tz = tzData[alpha_2]
    if alpha_2 == 'US':
        state = us.states.lookup(params['state']).abbr
        tz = tz[state]

    data = {"$set": {'_id': params['user'], 'discordID' : params['user'], 'tz' : tz }}

    db.userTimezone.update_one({'_id' : params['user']}, data, upsert=True)
    return {'Result' : tz}

# @app.route('/delUserData/')
# def deluserdata():
#     db.userData.delete_many({})
#     return "Deleted everything bro"

# @app.route('/delRaceData/')
# def delracedata():
#     db.raceData.delete_many({})
#     return "Deleted everything bro"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105, debug=True)

# use virtual env - .\f1API\Scripts\activate
# helpful link - https://towardsdatascience.com/creating-restful-apis-using-flask-and-python-655bad51b24
# mongoDB mods - https://medium.com/@gokulprakash22/getting-started-with-flask-pymongo-d6326db2a9a7
