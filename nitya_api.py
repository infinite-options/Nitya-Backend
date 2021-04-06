#To run program:  python3 io_api.py 

#README:  if conn error make sure password is set properly in RDS PASSWORD section

#README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)

#README:  if there are errors, make sure you have all requirements are loaded
#pip3 install flask
#pip3 install flask_restful
#pip3 install flask_cors
#pip3 install Werkzeug
#pip3 install pymysql
#pip3 install python-dateutil

import os
import uuid
import boto3
import json
import math

from datetime import time,date,datetime,timedelta

from pytz import timezone
import random
import string
import stripe

from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message
# used for serializer email and error handling
#from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
#from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.security import generate_password_hash, \
     check_password_hash


#  NEED TO SOLVE THIS
# from NotificationHub import Notification
# from NotificationHub import NotificationHub

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from twilio.rest import Client

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil
import string
import random

# BING API KEY
# Import Bing API key into bing_api_key.py

#  NEED TO SOLVE THIS
# from env_keys import BING_API_KEY, RDS_PW

import decimal
import sys
import json
import pytz
import pymysql
import requests

#RDS_HOST = 'pm-mysqldb.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
RDS_HOST = 'io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
#RDS_HOST = 'localhost'
RDS_PORT = 3306
#RDS_USER = 'root'
RDS_USER = 'admin'
#RDS_DB = 'feed_the_hungry'
RDS_DB = 'nitya'

#app = Flask(__name__)
app = Flask(__name__, template_folder='assets')

# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead
import stripe
stripe_public_key = 'pk_test_6RSoSd9tJgB2fN2hGkEDHCXp00MQdrK3Tw'
stripe_secret_key = 'sk_test_fe99fW2owhFEGTACgW3qaykd006gHUwj1j'

#this is a testing key using ptydtesting's stripe account.
# stripe_public_key = "pk_test_51H0sExEDOlfePYdd9TVlnhVDOCmmnmdxAxyAmgW4x7OI0CR7tTrGE2AyrTk8VjftoigEOhv2RTUv5F8yJrfp4jWQ00Q6KGXDHV"
# stripe_secret_key = "sk_test_51H0sExEDOlfePYdd9UQDxfp8yoY7On272hCR9ti12WSNbIGTysaJI8K2W8NhCKqdBOEhiNj4vFOtQu6goliov8vF00cvqfWG6d"

stripe.api_key = stripe_secret_key
# Allow cross-origin resource sharing
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# --------------- Mail Variables ------------------
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('PASSWORD')
# app.config['MAIL_USERNAME'] = ''
# app.config['MAIL_PASSWORD'] = ''

# Setting for mydomain.com
app.config['MAIL_SERVER'] = 'smtp.mydomain.com'
app.config['MAIL_PORT'] = 465

# Setting for gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465

app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True



# Set this to false when deploying to live application
#app.config['DEBUG'] = True
app.config['DEBUG'] = False

app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY')

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc
def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
def getNow(): return datetime.strftime(datetime.now(utc),"%Y-%m-%d %H:%M:%S")

# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""

# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = '******'
# RDS_PW = RdsPw()


#s3 = boto3.client('s3')

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('MEAL_IMAGES_BUCKET')
#BUCKET_NAME = 'servingnow'
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])



getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.environ.get('NOTIFICATION_HUB_KEY')
NOTIFICATION_HUB_NAME = os.environ.get('NOTIFICATION_HUB_NAME')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')	
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect( host=RDS_HOST,
                                user=RDS_USER,
                                port=RDS_PORT,
                                passwd=RDS_PW,
                                db=RDS_DB,
                                cursorclass=pymysql.cursors.DictCursor)
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")

# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")

# Serialize JSON
def serializeResponse(response):
    try:
        print("In Serialize JSON")
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        print("In Serialize JSON response", response)
        return response
    except:
        raise Exception("Bad query JSON")


# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization = False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is 'get':
                result = cur.fetchall()
                response['message'] = 'Successfully executed SQL query.'
                # Return status code of 280 for successful GET request
                response['code'] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response['result'] = result
            elif cmd in 'post':
                conn.commit()
                response['message'] = 'Successfully committed SQL command.'
                # Return status code of 281 for successful POST request
                response['code'] = 281
            else:
                response['message'] = 'Request failed. Unknown or ambiguous instruction given for MySQL command.'
                # Return status code of 480 for unknown HTTP method
                response['code'] = 480
    except:
        response['message'] = 'Request failed, could not execute MySQL command.'
        # Return status code of 490 for unsuccessful HTTP request
        response['code'] = 490
    finally:
        response['sql'] = sql
        return response

# Close RDS connection
def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")

# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples
def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")


# ===========================================================


# -- Queries start here -------------------------------------------------------------------------------

# -- 1.  GET Query
class appointments(Resource):
    # QUERY 1 RETURNS ALL BUSINESSES
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # This is the actual query
            query = """ # QUERY 1 
                 SELECT * FROM nitya.customers, nitya.treatments, nitya.appointments WHERE customer_uid = appt_customer_uid AND treatment_uid = appt_treatment_uid; """
            # The query is executed here
            items = execute(query, 'get', conn)
            # The return message and result from query execution
            response['message'] = 'successful'
            response['result'] = items['result']
            # Returns code and response
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
            
        # ENDPOINT THAT WORKS
        # http://localhost:4000/api/v2/appointments

class treatments(Resource):
    # QUERY 1 RETURNS ALL BUSINESSES
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # This is the actual query
            query = """ # QUERY 1 
                 SELECT * FROM  nitya.treatments; """
            # The query is executed here
            items = execute(query, 'get', conn)
            # The return message and result from query execution
            response['message'] = 'successful'
            response['result'] = items['result']
            # Returns code and response
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
        
        # http://localhost:4000/api/v2/treatments



class OneCustomerAppointments(Resource):
    # QUERY 2 RETURNS A SPECIFIC BUSINESSES
    def get(self, customer_uid):
        response = {}
        items = {}
        print("appointment_uid", customer_uid)
        try:
            conn = connect()
            query = """
                    SELECT * FROM nitya.appointments
                    WHERE appt_customer_uid = \'""" + customer_uid + """\';
                    """
            items = execute(query, 'get', conn)

            response['message'] = 'Specific Appointment successful'
            response['result'] = items['result']
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
        


class FullBlog(Resource):
    # QUERY 2 RETURNS A SPECIFIC BUSINESSES
    def get(self,blog_id):
        response = {}
        items = {}
        try:
            conn = connect()
            query = """
                    SELECT * FROM nitya.blog
                    WHERE blog_uid = \'""" + blog_id + """\';
                    """
            items = execute(query, 'get', conn)

            response['message'] = 'Specific Blog successful'
            response['result'] = items['result']
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class TruncatedBlog(Resource):
    # QUERY 2 RETURNS A SPECIFIC BUSINESSES
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            query = """
                    SELECT blog_uid,blogCategory,blogTitle,slug,postedOn,author,blogImage,LEFT(blogText, 200) AS blogText FROM blog ;
                    """
            items = execute(query, 'get', conn)

            response['message'] = 'Specific Blog successful'
            response['result'] = items['result']
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class CreateAppointment(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)
            customer_uid = data['appt_customer_uid']
            treatment_uid = data['appt_treatment_uid']
            notes = data['notes']
            datevalue= data['appt_date']
            timevalue = data['appt_time']
            print('customer_uid', customer_uid)
            print('treatment_uid', treatment_uid)
            print('notes', notes)
            print('date', datevalue)
            print('time', timevalue)


            #Query [0]  Get New UID
            #query = ["CALL new_refund_uid;"]
            query = ["CALL nitya.new_appointment_uid;"]
            NewIDresponse = execute(query[0], 'get', conn)
            NewID = NewIDresponse['result'][0]['new_id']
            print("NewID = ", NewID) 
            # NewID is an Array and new_id is the first element in that array
            
        

            query = """INSERT INTO appointments
                                (appointment_uid
                                    , appt_customer_uid
                                    , appt_treatment_uid
                                    , notes
                                    , appt_date
                                    , appt_time
                                    ) 
                                VALUES
                                (     \'""" +  NewID  + """\'
                                    , \'""" + customer_uid + """\'
                                    , \'""" + treatment_uid + """\'
                                    , \'""" + notes + """\'
                                    , \'""" + datevalue + """\'
                                    , \'""" + timevalue + """\');"""
            items = execute(query,'post',conn)

            response['message'] = 'Appointments Post successful'
            response['result'] = items
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointment
        
            # {"appt_customer_id":"100-00090",
            #  "appt_treatment_uid":"200-0000",
            #  "notes":"deefefef",
            #  "appt_date":"12:12:21",
            #   "appt_time":"14:00"}

class AddTreatment(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            #print("Received:", data)
            
            title = data['title']
            description = data['description']
            cost = data['cost']
            availability= data['availability']
            duration = data['duration']
            image_url = data['image_url']
            

            query = ["CALL nitya.new_treatment_uid;"]
            NewIDresponse = execute(query[0], 'get', conn)
            NewID = NewIDresponse['result'][0]['new_id']
            print("NewID = ", NewID) 
        

            query = """INSERT INTO treatments
                                (treatment_uid
                                    , title
                                    , description
                                    , cost
                                    , availability
                                    , duration
                                    , image_url
                                    ) 
                                VALUES
                                (     \'""" + NewID + """\'
                                    , \'""" + title + """\'
                                    , \'""" + description + """\'
                                    , \'""" + cost + """\'
                                    , \'""" + availability + """\'
                                    , \'""" + duration + """\'
                                    , \'""" + image_url+ """\');"""
            items = execute(query,'post',conn)

            response['message'] = 'Treatments Post successful'
            response['result'] = items
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class AddBlog(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            #print("Received:", data)
            
            
            blogCategory = data['blogCategory']
            blogTitle = data['blogTitle']
            slug= data['slug']
            author = data['author']
            blogImage = data['blogImage']
            blogText = data['blogText']
            

            query = ["CALL nitya.new_blog_uid;"]
            NewIDresponse = execute(query[0], 'get', conn)
            NewID = NewIDresponse['result'][0]['new_id']
            print("NewID = ", NewID) 
        

            query = """INSERT INTO blog
                                (blog_uid 
                                    , blogCategory
                                    , blogTitle
                                    , slug
                                    , author
                                    , blogImage
                                    , blogText
                                    ) 
                                VALUES
                                (     \'""" + NewID + """\'
                                    , \'""" + blogCategory + """\'
                                    , \'""" + blogTitle + """\'
                                    , \'""" + slug + """\'
                                    , \'""" + author + """\'
                                    , \'""" + blogImage + """\'
                                    , \'""" + blogText+ """\');"""
            items = execute(query,'post',conn)

            response['message'] = 'Blog Post successful'
            
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class Calendar(Resource):
    # QUERY 1 RETURNS ALL BUSINESSES
    def get(self):
        response = {}
        items = {}
        modified_items ={}
        try:
            # Connect to the DataBase
            conn = connect()
            # This is the actual query
            #query = """ # QUERY 1 
            #     SELECT * FROM nitya.calendar_dates LEFT JOIN nitya.Practioner_availability ON calendar_date = date; """
            # The query is executed here
            query = """ # QUERY 1 
                SELECT calendar_dates.calendar_date, calendar_dates.start_time, calendar_dates.end_time, Practioner_availability.start_time_notavailable, Practioner_availability.end_time_notavailable, appointments.appt_time, appointments.appt_treatment_uid, treatments.duration FROM  nitya.calendar_dates LEFT JOIN nitya.Practioner_availability ON calendar_date = date LEFT JOIN appointments on calendar_date = appt_date LEFT JOIN treatments on appt_treatment_uid = treatment_uid; """
            # The query is executed here
            items = execute(query, 'get', conn)
            #print("Before function")
            modified_items = self.getavailabletimes(items)
            # The return message and result from query execution

            response['message'] = 'successful'
            response['result'] = modified_items
            # Returns code and response
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

    def gethalfhourtimeslots(self, st, et):
        l=[]
        while(st < et):
            l.append(st.time())
            st = st+timedelta(minutes=30)
        return l

    def diff_list(self, li1, li2):
        return (list(list(set(li1)-set(li2)) + list(set(li2)-set(li1))))



    def getavailabletimes(self,items):
        availability = {}
        timeslots = {}
        booked_appt = {}
        result = []
        for obj in items['result']:
            calendar_date = obj['calendar_date']
            
            # To Calculate the day timeslots based on the start and end time(timeslots dictionary, key - date, value- list of 30 min time objects)
            day_start_time = obj['start_time']
            day_end_time =obj['end_time']
            st = time(hour = int(day_start_time.split(":")[0]),minute = int(day_start_time.split(":")[1]), second = int(day_start_time.split(":")[2]))
            et =  time(hour = int(day_end_time.split(":")[0]),minute = int(day_end_time.split(":")[1]), second = int(day_end_time.split(":")[2]))
            st = datetime.combine(date.today(), st)
            et = datetime.combine(date.today(), et)
            if(calendar_date not in timeslots):
                timeslots[calendar_date] = self.gethalfhourtimeslots(st, et)
            #print (st)
            #print (et)

            # To Calculate the not available timeslots based on the start and end not available time(availability dictionary, key - date, value- list of 30 min time objects)
            start_time_notavailable = obj['start_time_notavailable']
            end_time_notavailable = obj['end_time_notavailable']
            #print(start_time_notavailable)
            #print(end_time_notavailable)
            if(start_time_notavailable != None and end_time_notavailable != None):
                st_na = time(hour = int(start_time_notavailable.split(":")[0]),minute = int(start_time_notavailable.split(":")[1]), second = int(start_time_notavailable.split(":")[2]))
                et_na = time(hour = int(end_time_notavailable.split(":")[0]),minute = int(end_time_notavailable.split(":")[1]), second = int(end_time_notavailable.split(":")[2]))
                st_na = datetime.combine(date.today(), st_na)
                et_na = datetime.combine(date.today(), et_na)
                if(calendar_date in availability):
                    availability[calendar_date] = availability[calendar_date] + self.gethalfhourtimeslots(st_na, et_na)
                else:
                    availability[calendar_date] = self.gethalfhourtimeslots(st_na, et_na)


            # To Calculate the appointments timeslots based on the duration of the appointment(booked_appt dictionary, key - date, value- list of 30 min time objects)
            appt_start_time = obj['appt_time']
            duration = obj['duration']
            if(appt_start_time != None and duration != None):
                appt_start_time = time(hour = int(appt_start_time.split(":")[0]),minute = int(appt_start_time.split(":")[1]), second = int(appt_start_time.split(":")[2]))
                duration =  timedelta(hours = int(duration.split(":")[0]),minutes = int(duration.split(":")[1]), seconds = int(duration.split(":")[2]))
                appt_start_time= datetime.combine(date.today(), appt_start_time)
                #print(appt_start_time)
                #print(duration)
                appt_end_time = appt_start_time +duration
                #print("End time")
                #print(appt_end_time)
                if(calendar_date in booked_appt):
                    booked_appt[calendar_date] = booked_appt[calendar_date] + self.gethalfhourtimeslots(appt_start_time, appt_end_time)
                else:
                    booked_appt[calendar_date] = self.gethalfhourtimeslots(appt_start_time, appt_end_time)

        # Removing not available timeslots from total timeslots
        for d in availability:
            if(d in timeslots):
                timeslots[d] = self.diff_list(timeslots[d],availability[d])
        
        # Removing booked available timeslots from the remaining timeslots
        for d in booked_appt:
            if(d in timeslots):
                timeslots[d] = self.diff_list(timeslots[d],booked_appt[d])

        # sorting the timeslots
        for k in timeslots:
            timeslots[k].sort()
            #print(k, timeslots[k])
        #print(timeslots)

        #The resultisof the format key=date, value= list of time objects, converting it to list of dictionaries,
        #where each dictionary is of the format key= "date", value = list of time string 
        for k in timeslots:
            temp_dict = {}
            temp_list = []
            for t in timeslots[k]:
                #print(t.strftime("%H:%M:%S"))
                temp_list.append(t.strftime("%H:%M:%S"))
            temp_dict["date"] = k
            temp_dict["available_timeslots"] = temp_list
            result.append(temp_dict)

        #print(timeslots)
        #items = serializeResponse(result)
        #print(items)
        #print('\n')

            
        return result

            


# -- DEFINE APIS -------------------------------------------------------------------------------




# Define API routes

api.add_resource(appointments, '/api/v2/appointments')
api.add_resource(treatments, '/api/v2/treatments')
api.add_resource(FullBlog, '/api/v2/fullblog/<string:blog_id>')
api.add_resource(TruncatedBlog, '/api/v2/truncatedblog')
api.add_resource(OneCustomerAppointments, '/api/v2/onecustomerappointments/<string:customer_uid>')
api.add_resource(CreateAppointment, '/api/v2/createappointment')
api.add_resource(AddTreatment, '/api/v2/addtreatment')
api.add_resource(AddBlog, '/api/v2/addblog')
api.add_resource(Calendar, '/api/v2/calendar')



# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)

