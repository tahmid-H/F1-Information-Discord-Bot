import enum
from flask_pymongo import PyMongo
from flask import Flask, jsonify, request
import fastf1 as ff1
import requests as rq
from bson.json_util import dumps
import sys


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://tahmid-H:F1-Data-2022@f1-data.6ge2m.mongodb.net/botData?retryWrites=true&w=majority"
mongodb_client = PyMongo(app)
db = mongodb_client.db

@app.route('/', methods=['GET', 'POST'])
def home():
    return "Homepage bro!"

@app.route('/test/')
def test():
    res = ff1.core.get_round(int(request.args['year']), request.args['keyword'])
    return str(res)

@app.route('/addNotification/')
def addnotification():
    data = request.args

    return jsonify(request.args)

@app.route('/initUserRoundData/')
def inituserrounddata():
    res = rq.get("https://ergast.com/api/f1/2022.json").json()
    user_notif_table = []
    for e in enumerate(res['MRData']['RaceTable']['Races']):
        data = e[1]
        user_notif_table.append({'_id':  str(data['season']) + str(data['round']) + str(data['raceName']).replace(" ", "") + str( data['Circuit']['circuitName']).replace(" ", ""), 'round': data['round'], 'raceName' : data['raceName'], 'circuitName' : data['Circuit']['circuitName'], 'FP1' : [], 'FP2': [], 'FP3': [], 'qualification': [], 'sprint': [], 'race': []})
    try:
        db.user_notifications.insert_many(user_notif_table, ordered = False )
    except Exception as e:
        print(e, file=sys.stderr)


    return jsonify("User Race Data Updated")

@app.route('/getUserRoundData/')
def getuserrounddata():
    ret = dict()
    cursor = db.user_notifications.find()
    i = 1
    for doc in cursor:
        ret[i] = doc
        i += 1
    return jsonify(dumps(ret))

# @app.route('/delUserRoundData/')
# def deluserrounddata():
#     db.user_notifications.delete_many({})
#     return "Deleted everything bro"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105, debug=True)

# use virtual env - .\f1API\Scripts\activate
# helpful link - https://towardsdatascience.com/creating-restful-apis-using-flask-and-python-655bad51b24
# request inclusion - http://localhost:105/test/?circuit=Monza&year=2021&driver=&scoop=yes
# mongoDB mods - https://medium.com/@gokulprakash22/getting-started-with-flask-pymongo-d6326db2a9a7
