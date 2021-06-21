# To run program:  python3 nitya_api.py

# README:  if conn error make sure password is set properly in RDS PASSWORD section

# README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)

# README:  if there are errors, make sure you have all requirements are loaded
# pip3 install flask
# pip3 install flask_restful
# pip3 install flask_cors
# pip3 install Werkzeug
# pip3 install pymysql
# pip3 install python-dateutil

import os
import uuid
import boto3
import json
import math


from datetime import time, date, datetime, timedelta
import calendar

from pytz import timezone
import random
import string
import stripe

from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message

# used for serializer email and error handling
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
# from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.security import generate_password_hash, check_password_hash


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

# RDS_HOST = 'pm-mysqldb.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
# RDS_HOST = 'localhost'
RDS_PORT = 3306
# RDS_USER = 'root'
RDS_USER = "admin"
# RDS_DB = 'feed_the_hungry'
RDS_DB = "nitya"

# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")









# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead
import stripe


# STRIPE AND PAYPAL KEYS
paypal_secret_test_key = os.environ.get('paypal_secret_key_test')
paypal_secret_live_key = os.environ.get('paypal_secret_key_live')

paypal_client_test_key = os.environ.get('paypal_client_test_key')
paypal_client_live_key = os.environ.get('paypal_client_live_key')

stripe_public_test_key = os.environ.get('stripe_public_test_key')
stripe_secret_test_key = os.environ.get('stripe_secret_test_key')

stripe_public_live_key = os.environ.get('stripe_public_live_key')
stripe_secret_live_key = os.environ.get('stripe_secret_live_key')

stripe.api_key = stripe_secret_test_key

#use below for local testing
#stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3"" 


CORS(app)

# --------------- Mail Variables ------------------
app.config["MAIL_USERNAME"] = os.environ.get("EMAIL")
app.config["MAIL_PASSWORD"] = os.environ.get("PASSWORD")
# app.config['MAIL_USERNAME'] = ''
# app.config['MAIL_PASSWORD'] = ''

# Setting for mydomain.com
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465

# Setting for gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465

app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True


# Set this to false when deploying to live application
# app.config['DEBUG'] = True
app.config["DEBUG"] = False

app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc


def getToday():
    return datetime.strftime(datetime.now(utc), "%Y-%m-%d")


def getNow():
    return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")


# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""


# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = "prashant"
# RDS_PW = RdsPw()


# s3 = boto3.client('s3')

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('MEAL_IMAGES_BUCKET')
# BUCKET_NAME = 'servingnow'
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])


getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.environ.get("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.environ.get("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            port=RDS_PORT,
            passwd=RDS_PW,
            db=RDS_DB,
            cursorclass=pymysql.cursors.DictCursor,
        )
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
        # print("In Serialize JSON")
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        # print("In Serialize JSON response", response)
        return response
    except:
        raise Exception("Bad query JSON")


# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization=False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd in "post":
                conn.commit()
                response["message"] = "Successfully committed SQL command."
                # Return status code of 281 for successful POST request
                response["code"] = 281
            else:
                response[
                    "message"
                ] = "Request failed. Unknown or ambiguous instruction given for MySQL command."
                # Return status code of 480 for unknown HTTP method
                response["code"] = 480
    except:
        response["message"] = "Request failed, could not execute MySQL command."
        # Return status code of 490 for unsuccessful HTTP request
        response["code"] = 490
    finally:
        response["sql"] = sql
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
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """  
                 SELECT * 
                 FROM nitya.customers, 
                    nitya.treatments, 
                    nitya.appointments 
                WHERE customer_uid = appt_customer_uid 
                    AND treatment_uid = appt_treatment_uid;
                     """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT THAT WORKS
        # http://localhost:4000/api/v2/appointments


class treatments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 2
            query = """  
                 SELECT * FROM  nitya.treatments; """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)

        # http://localhost:4000/api/v2/treatments


class OneCustomerAppointments(Resource):
    def get(self, customer_uid):
        response = {}
        items = {}
        print("appointment_uid", customer_uid)
        try:
            conn = connect()
            # QUERY 3
            query = (
                """
                    SELECT * FROM nitya.appointments
                    WHERE appt_customer_uid = \'""" + customer_uid + """\';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Appointment successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Customer Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)


class FullBlog(Resource):
    def get(self, blog_id):
        response = {}
        items = {}
        try:
            conn = connect()
             # QUERY 4
            query = (
                """
                    SELECT * FROM nitya.blog
                    WHERE blog_uid = \'""" + blog_id + """\';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Full Blog Request failed, please try again later.")
        finally:
            disconnect(conn)


class TruncatedBlog(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
             # QUERY 5
            query = """
                    SELECT blog_uid,blogCategory,blogTitle,slug,postedOn,author,blogImage,LEFT(blogText, 200) AS blogText FROM nitya.blog ;
                    """
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Specific Blog Request failed, please try again later.")
        finally:
            disconnect(conn)


class CreateAppointment(Resource):
    def post(self):
        response = {}
        items = {}
        cus_id = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)
            first_name = data["first_name"]
            last_name = data["last_name"]
            email = data["email"]
            phone_no = data["phone_no"]
            treatment_uid = data["appt_treatment_uid"]
            notes = data["notes"]
            datevalue = data["appt_date"]
            timevalue = data["appt_time"]
            purchase_price = data["purchase_price"]
            purchase_date = data["purchase_date"]

            print("first_name", first_name)
            print("last_name", last_name)
            print("email", email)
            print("phone_no", phone_no)
            print("treatment_uid", treatment_uid)
            print("notes", notes)
            print("date", datevalue)
            print("time", timevalue)
            print("purchase_price", purchase_price)
            print("purchase_date", purchase_date)

            # Query [0]  Get New UID
            # query = ["CALL new_refund_uid;"]
            query = ["CALL nitya.new_appointment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)
            # NewID is an Array and new_id is the first element in that array

            query1 = (
                """ 
                    SELECT customer_uid FROM nitya.customers 
                    WHERE customer_first_name = \'""" + first_name + """\' 
                    AND   customer_last_name = \'""" + last_name + """\' 
                    AND   customer_email = \'""" + email + """\' 
                    AND   customer_phone_num = \'""" + phone_no + """\';
                """
            )
            cus_id = execute(query1, "get", conn)
            print(cus_id["result"])
            for obj in cus_id["result"]:
                NewcustomerID = obj["customer_uid"]
                print(NewcustomerID)

            print(len(cus_id["result"]))

            if len(cus_id["result"]) == 0:
                query = ["CALL nitya.new_customer_uid;"]
                NewIDresponse = execute(query[0], "get", conn)
                NewcustomerID = NewIDresponse["result"][0]["new_id"]
                customer_insert_query = (
                    """
                        INSERT INTO nitya.customers 
                        (
                            customer_uid,
                            customer_first_name,
                            customer_last_name,
                            customer_phone_num,
                            customer_email
                        )
                        VALUES
                        (
                            \'""" + NewcustomerID + """\',
                            \'""" + first_name + """\',
                            \'""" + last_name + """\',
                            \'""" + phone_no + """\',
                            \'""" + email + """\'
                        );
                    """
                )

                customer_items = execute(customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)
            else:
                for obj in cus_id["result"]:
                    NewcustomerID = obj["customer_uid"]
                    print("customerID = ", NewcustomerID)

            #  convert to new format:  payment_time_stamp = \'''' + getNow() + '''\',
            query2 = (
                """
                    INSERT INTO appointments
                    (   appointment_uid
                        , appt_customer_uid
                        , appt_treatment_uid
                        , notes
                        , appt_date
                        , appt_time
                        , purchase_price
                        , purchase_date
                    ) 
                    VALUES
                    (     \'""" + NewID + """\'
                        ,\'""" + NewcustomerID + """\'
                        ,\'""" + treatment_uid + """\'
                        ,\'""" + notes + """\'
                        ,\'""" + datevalue + """\'
                        ,\'""" + timevalue + """\'
                        ,\'""" + purchase_price + """\'
                        ,\'""" + purchase_date + """\'
                    );
                """
            )
            items = execute(query2, "post", conn)

            response["message"] = "Appointments Post successful"
            response["result"] = items
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

        # ENDPOINT AND JSON OBJECT THAT WORKS
        # http://localhost:4000/api/v2/createappointment


class AddTreatment(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            availability = data["availability"]
            duration = data["duration"]
            image_url = data["image_url"]

            query = ["CALL nitya.new_treatment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO treatments
                    (   treatment_uid
                        , title
                        , category
                        , description
                        , cost
                        , availability
                        , duration
                        , image_url
                    ) 
                    VALUES
                    (     \'""" + NewID + """\'
                        , \'""" + title + """\'
                        , \'""" + category + """\'
                        , \'""" + description + """\'
                        , \'""" + cost + """\'
                        , \'""" + availability + """\'
                        , \'""" + duration + """\'
                        , \'""" + image_url + """\'
                    );
                """
            )
            items = execute(query, "post", conn)

            response["message"] = "Treatments Post successful"
            response["result"] = items
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
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
            # print("Received:", data)

            blogCategory = data["blogCategory"]
            blogTitle = data["blogTitle"]
            slug = data["slug"]
            postedOn = data["postedOn"]
            author = data["author"]
            blogImage = data["blogImage"]
            blogText = data["blogText"]

            query = ["CALL nitya.new_blog_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """INSERT INTO blog
                                (blog_uid 
                                    , blogCategory
                                    , blogTitle
                                    , slug
                                    , postedOn
                                    , author
                                    , blogImage
                                    , blogText
                                    ) 
                                VALUES
                                (     \'""" + NewID + """\'
                                    , \'""" + blogCategory + """\'
                                    , \'""" + blogTitle + """\'
                                    , \'""" + slug + """\'
                                    , \'""" + postedOn + """\'
                                    , \'""" + author + """\'
                                    , \'""" + blogImage + """\'
                                    , \'""" + blogText + """\');"""
            )
            items = execute(query, "post", conn)

            response["message"] = "Blog Post successful"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class AddContact(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            name = data["name"]
            email = data["email"]
            subject = data["subject"]
            message = data["message"]

            query = (
                """INSERT INTO contact
                                (name
                                    , email
                                    , subject
                                    , message
                                    ) 
                                VALUES
                                (     \'""" + name + """\'
                                    , \'""" + email + """\'
                                    , \'""" + subject + """\'
                                    , \'""" + message + """\');"""
            )
            items = execute(query, "post", conn)

            response["message"] = "Contact Post successful"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class purchaseDetails(Resource):
    # QUERY 1 RETURNS ALL BUSINESSES
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # This is the actual query
            query = """ # QUERY 1 
                 SELECT appointment_uid,customer_first_name,customer_last_name,customer_phone_num, customer_email,appt_date,appt_time,purchase_price, purchase_date,cost, appt_treatment_uid,title FROM appointments LEFT JOIN customers ON appt_customer_uid = customer_uid LEFT JOIN treatments ON appt_treatment_uid = treatment_uid; """

            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution

            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)



class Calendar(Resource):
    def get(self, date_value):
        print("\nInside Calendar Availability")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", id)

            # CALCULATE AVAILABLE TIME SLOTS
            query = """
                    SELECT 
                        TIME_FORMAT(ts_begin, '%T') AS appt_start,
                        TIME_FORMAT(ts_end, '%T') AS appt_end
                        -- *,
                        -- TIMEDIFF(stop_time,begin_time),
                        -- IF (ISNULL(taadpa.appointment_uid) AND ISNULL(taadpa.prac_avail_uid) AND !ISNULL(days_uid), "Available", "Not Available") AS AVAILABLE
                    FROM(
                        -- GET TIME SLOTS
                        SELECT ts.*,
                            TIME(ts.begin_time) AS ts_begin,
                            TIME(ts.stop_time) AS ts_end,
                            appt_dur.*,
                            pa.*,
                            openhrs.*
                        FROM nitya.time_slots ts
                        -- GET CURRENT APPOINTMENTS
                        LEFT JOIN (
                            SELECT -- *,
                                appointment_uid,
                                appt_date,
                                appt_time AS start_time,
                                duration,
                                ADDTIME(appt_time, duration) AS end_time,
                                cast(concat(appt_date, ' ', appt_time) as datetime) as start,
                                cast(concat(appt_date, ' ', ADDTIME(appt_time, duration)) as datetime) as end
                            FROM nitya.appointments
                            LEFT JOIN nitya.treatments
                            ON appt_treatment_uid = treatment_uid    
                            WHERE appt_date = "2021-06-13") AS appt_dur
                        ON TIME(ts.begin_time) = appt_dur.start_time
                            OR (TIME(ts.begin_time) > appt_dur.start_time AND TIME(ts.stop_time) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM nitya.practioner_availability
                            WHERE date = "2021-06-13") AS pa
                        ON TIME(ts.begin_time) = pa.start_time_notavailable
                            OR (TIME(ts.begin_time) > pa.start_time_notavailable AND TIME(ts.stop_time) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                                -- ADDTIME(morning_start_time, "0:29"),
                                -- if(morning_start_time = "9:00:00","Y","N")
                            FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK("2021-06-13")) AS openhrs
                        ON TIME(ts.begin_time) = openhrs.morning_start_time
                            OR (TIME(ts.begin_time) > openhrs.morning_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_time) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_time) > openhrs.afternoon_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.afternoon_end_time,"0:29")) 
                        )AS taadpa
                    WHERE ISNULL(taadpa.appointment_uid) 
                        AND ISNULL(taadpa.prac_avail_uid)
                        AND !ISNULL(days_uid)
                    """

            available_times = execute(query, 'get', conn)
            print("Available Times: ", str(available_times['result']))
            print("Number of time slots: ", len(available_times['result']))
            print("Available Times: ", str(available_times['result'][0]["appt_start"]))

            return available_times['result']

        except:
            raise BadRequest('Available Time Request failed, please try again later.')
        finally:
            disconnect(conn)




class Calendar_original(Resource):
    print("did it get here")
    def get(self, treatment_uid, date_value):
        response = {}
        items = {}
        modified_items = {}
        # print(date_value)
        # day_value = datetime.strptime(date_value, "%m-%d-%Y").weekday()
        day_value = datetime.strptime(date_value, "%Y-%m-%d").weekday()
        modified_date_value = date_value.replace("-", "/")
        print(modified_date_value)

        day = calendar.day_name[day_value]
        # print(day)
        try:
            # Connect to the DataBase
            conn = connect()
            query = (
                """ # QUERY 1 
                SELECT * FROM nitya.days WHERE day= \'"""
                + day
                + """\';"""
            )
            # The query is executed here

            query2 = (
                """ # QUERY 2
                SELECT * FROM appointments JOIN treatments on appt_treatment_uid = treatment_uid WHERE appt_date = \'"""
                + modified_date_value
                + """\';"""
            )

            query3 = (
                """ # QUERY 3
                SELECT * FROM nitya.practioner_availability  WHERE date = \'"""
                + modified_date_value
                + """\' ;"""
            )
            query4 = (
                """ # QUERY 4
                SELECT * FROM nitya.treatments WHERE treatment_uid= \'"""
                + treatment_uid
                + """\';"""
            )
            # The query is executed here

            day_time_duration = execute(query, "get", conn)
            booked_appointments = execute(query2, "get", conn)

            items = execute(query3, "get", conn)

            treatment_duration = execute(query4, "get", conn)

            day_calculation = self.calculation_result(
                day_time_duration,
                items,
                booked_appointments,
                treatment_duration,
                modified_date_value,
                treatment_uid,
                day,
            )

            response["message"] = "successful"
            response["result"] = day_calculation
            # Returns code and response
            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

    def gethalfhourtimeslots(self, st, et):
        l = []
        while st < et:
            l.append(st.time())
            st = st + timedelta(minutes=30)
        return l

    def diff_list(self, li1, li2):
        return list(list(set(li1) - set(li2)))

    def calculation_result(
        self,
        day_time_duration,
        items,
        booked_appointments,
        treatment_duration,
        modified_date_value,
        treatment_uid,
        day,
    ):
        morning_timeslots = []
        afternoon_timeslots = []
        not_available_timeslots = []
        booked_appointment_slots = []
        treatment_id_timeslots = []
        result = {}

        # print("Inside calculation_result")
        # print(day_time_duration['result'])
        # print(items['result'])

        for obj in day_time_duration["result"]:
            morning_start_time = obj["morning_start_time"]
            morning_end_time = obj["morning_end_time"]
            afternoon_start_time = obj["afternoon_start_time"]
            afternoon_end_time = obj["afternoon_end_time"]

            if morning_start_time != None and morning_end_time != None:
                m_st = time(
                    hour=int(morning_start_time.split(":")[0]),
                    minute=int(morning_start_time.split(":")[1]),
                    second=int(morning_start_time.split(":")[2]),
                )
                m_et = time(
                    hour=int(morning_end_time.split(":")[0]),
                    minute=int(morning_end_time.split(":")[1]),
                    second=int(morning_end_time.split(":")[2]),
                )
                m_st = datetime.combine(date.today(), m_st)
                m_et = datetime.combine(date.today(), m_et)
                morning_timeslots = self.gethalfhourtimeslots(m_st, m_et)
                # print("morning_timeslots")
                # print(morning_timeslots)

            if len(afternoon_start_time) != 0 and len(afternoon_end_time) != 0:
                # print(len(afternoon_start_time), len(afternoon_end_time))
                a_st = time(
                    hour=int(afternoon_start_time.split(":")[0]),
                    minute=int(afternoon_start_time.split(":")[1]),
                    second=int(afternoon_start_time.split(":")[2]),
                )
                a_et = time(
                    hour=int(afternoon_end_time.split(":")[0]),
                    minute=int(afternoon_end_time.split(":")[1]),
                    second=int(afternoon_end_time.split(":")[2]),
                )
                a_st = datetime.combine(date.today(), a_st)
                a_et = datetime.combine(date.today(), a_et)
                afternoon_timeslots = self.gethalfhourtimeslots(a_st, a_et)
                # print("afternoon_timeslots")
                # print(afternoon_timeslots)

        # print("total timeslots")
        total_timeslots = morning_timeslots + afternoon_timeslots
        # print(total_timeslots)
        # print("At the end of calculation_result")

        for obj in items["result"]:
            print("inside items")
            start_time_notavailable = obj["start_time_notavailable"]
            end_time_notavailable = obj["end_time_notavailable"]
            # print(start_time_notavailable)
            # print(end_time_notavailable)
            if start_time_notavailable != None and end_time_notavailable != None:
                st_na = time(
                    hour=int(start_time_notavailable.split(":")[0]),
                    minute=int(start_time_notavailable.split(":")[1]),
                    second=int(start_time_notavailable.split(":")[2]),
                )
                et_na = time(
                    hour=int(end_time_notavailable.split(":")[0]),
                    minute=int(end_time_notavailable.split(":")[1]),
                    second=int(end_time_notavailable.split(":")[2]),
                )
                st_na = datetime.combine(date.today(), st_na)
                et_na = datetime.combine(date.today(), et_na)

                if not not_available_timeslots:
                    not_available_timeslots = self.gethalfhourtimeslots(st_na, et_na)
                else:
                    not_available_timeslots = not_available_timeslots + (
                        self.gethalfhourtimeslots(st_na, et_na)
                    )

        # print(not_available_timeslots)

        for obj in booked_appointments["result"]:
            # print(booked_appointments['result'])
            appt_start_time = obj["appt_time"]
            duration = obj["duration"]
            if appt_start_time != None and duration != None:
                appt_start_time = time(
                    hour=int(appt_start_time.split(":")[0]),
                    minute=int(appt_start_time.split(":")[1]),
                    second=int(appt_start_time.split(":")[2]),
                )
                duration = timedelta(
                    hours=int(duration.split(":")[0]),
                    minutes=int(duration.split(":")[1]),
                    seconds=int(duration.split(":")[2]),
                )
                appt_start_time = datetime.combine(date.today(), appt_start_time)
                # print(appt_start_time)
                # print(duration)
                appt_end_time = appt_start_time + duration
                # print("End time")
                # print(appt_end_time)
                if not booked_appointment_slots:
                    booked_appointment_slots = self.gethalfhourtimeslots(
                        appt_start_time, appt_end_time
                    )
                else:
                    booked_appointment_slots = booked_appointment_slots + (
                        self.gethalfhourtimeslots(appt_start_time, appt_end_time)
                    )
            # print("booked_appointments")
            # print(booked_appointment_slots)

        available_timeslots_calculation = self.diff_list(
            total_timeslots, not_available_timeslots
        )
        # print(available_timeslots_calculation)
        total_available_timeslots = self.diff_list(
            available_timeslots_calculation, booked_appointment_slots
        )

        # print("Available timeslots for a day")
        total_available_timeslots.sort()
        # print(total_available_timeslots)

        for obj in treatment_duration["result"]:
            t_duration = obj["duration"]
            t_duration_min = int(t_duration.split(":")[0]) * 60 + int(
                t_duration.split(":")[1]
            )
            t_duration_roundoff = int(t_duration_min / 30) * 30 + (
                30 if t_duration_min % 30 != 0 else 0
            )
            num_minutes = timedelta(minutes=t_duration_roundoff)
            num_30_slots = int(t_duration_roundoff / 30)
            # print("Total Minutes")
            # print(num_minutes)
            # print(num_30_slots)

        for s_time in total_available_timeslots:
            # print(s_time)
            s_time = datetime.combine(date.today(), s_time)
            dont_use_s_time = 0
            for i in range(1, num_30_slots):
                # print(i)
                # print(s_time + timedelta(minutes=30*i))
                if (
                    (s_time + timedelta(minutes=30 * i)).time()
                ) not in total_available_timeslots:
                    dont_use_s_time = 1
                    continue
            if dont_use_s_time == 0:
                treatment_id_timeslots.append(s_time.time())

        temp_list = []
        for t in treatment_id_timeslots:
            # print(t.strftime("%H:%M:%S"))
            temp_list.append(t.strftime("%H:%M:%S"))

        result["date"] = modified_date_value
        result["day"] = day
        result["treatment_uid"] = treatment_uid
        result["available_timeslots"] = temp_list
        """temp_list =[]   
        for t in total_available_timeslots:
            #print(t.strftime("%H:%M:%S"))
            temp_list.append(t.strftime("%H:%M:%S"))
        result["pre_available_timeslots"] = temp_list"""
        result["treatment_duration"] = t_duration_min

        return result

# --------------



class createAccount(Resource):
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            firstName = data["first_name"]
            lastName = data["last_name"]
            phone = data["phone_number"]
            address = data["address"]
            unit = data["unit"] if data.get("unit") is not None else "NULL"
            social_id = (
                data["social_id"] if data.get("social_id") is not None else "NULL"
            )
            city = data["city"]
            state = data["state"]
            zip_code = data["zip_code"]
            latitude = data["latitude"]
            longitude = data["longitude"]
            referral = data["referral_source"]
            role = data["role"]
            cust_id = data["cust_id"] if data.get("cust_id") is not None else "NULL"

            if (
                data.get("social") is None
                or data.get("social") == "FALSE"
                or data.get("social") == False
                or data.get("social") == "NULL"
            ):
                social_signup = False
            else:
                social_signup = True

            print(social_signup)
            get_user_id_query = "CALL new_customer_uid();"
            NewUserIDresponse = execute(get_user_id_query, "get", conn)

            print("New User Code: ", NewUserIDresponse["code"])

            if NewUserIDresponse["code"] == 490:
                string = " Cannot get new User id. "
                print("*" * (len(string) + 10))
                print(string.center(len(string) + 10, "*"))
                print("*" * (len(string) + 10))
                response["message"] = "Internal Server Error."
                return response, 500
            NewUserID = NewUserIDresponse["result"][0]["new_id"]
            print("New User ID: ", NewUserID)

            if social_signup == False:

                salt = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

                password = sha512((data["password"] + salt).encode()).hexdigest()
                print("password------", password)
                algorithm = "SHA512"
                mobile_access_token = "NULL"
                mobile_refresh_token = "NULL"
                user_access_token = "NULL"
                user_refresh_token = "NULL"
                user_social_signup = "NULL"
            else:

                mobile_access_token = data["mobile_access_token"]
                mobile_refresh_token = data["mobile_refresh_token"]
                user_access_token = data["user_access_token"]
                user_refresh_token = data["user_refresh_token"]
                salt = "NULL"
                password = "NULL"
                algorithm = "NULL"
                user_social_signup = data["social"]

                print("ELSE- OUT")

            if cust_id != "NULL" and cust_id:

                NewUserID = cust_id

                query = (
                    """
                        SELECT user_access_token, user_refresh_token, mobile_access_token, mobile_refresh_token 
                        FROM nitya.customers
                        WHERE customer_uid = \'""" + cust_id + """\';
                    """
                )
                it = execute(query, "get", conn)
                print("it-------", it)

                if it["result"][0]["user_access_token"] != "FALSE":
                    user_access_token = it["result"][0]["user_access_token"]

                if it["result"][0]["user_refresh_token"] != "FALSE":
                    user_refresh_token = it["result"][0]["user_refresh_token"]

                if it["result"][0]["mobile_access_token"] != "FALSE":
                    mobile_access_token = it["result"][0]["mobile_access_token"]

                if it["result"][0]["mobile_refresh_token"] != "FALSE":
                    mobile_refresh_token = it["result"][0]["mobile_refresh_token"]

                customer_insert_query = [
                    """
                        UPDATE nitya.customers 
                        SET 
                        customer_created_at = \'"""+ (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+ """\',
                        customer_first_name = \'"""+ firstName+ """\',
                        customer_last_name = \'"""+ lastName+ """\',
                        customer_phone_num = \'"""+ phone+ """\',
                        customer_address = \'"""+ address+ """\',
                        customer_unit = \'"""+ unit+ """\',
                        customer_city = \'"""+ city+ """\',
                        customer_state = \'"""+ state+ """\',
                        customer_zip = \'"""+ zip_code+ """\',
                        customer_lat = \'"""+ latitude+ """\',
                        customer_long = \'"""+ longitude+ """\',
                        password_salt = \'"""+ salt+ """\',
                        password_hashed = \'"""+ password+ """\',
                        password_algorithm = \'"""+ algorithm+ """\',
                        referral_source = \'"""+ referral+ """\',
                        role = \'"""+ role+ """\',
                        user_social_media = \'"""+ user_social_signup+ """\',
                        social_timestamp  =  DATE_ADD(now() , INTERVAL 14 DAY)
                        WHERE customer_uid = \'"""+ cust_id+ """\';
                    """
                ]

            else:

                # check if there is a same customer_id existing
                query = (
                    """
                        SELECT customer_email FROM nitya.customers
                        WHERE customer_email = \'"""
                    + email
                    + "';"
                )
                print("email---------")
                items = execute(query, "get", conn)
                if items["result"]:

                    items["result"] = ""
                    items["code"] = 409
                    items["message"] = "Email address has already been taken."

                    return items

                if items["code"] == 480:

                    items["result"] = ""
                    items["code"] = 480
                    items["message"] = "Internal Server Error."
                    return items

                print("Before write")
                # write everything to database
                customer_insert_query = [
                    """
                        INSERT INTO nitya.customers 
                        (
                            customer_uid,
                            customer_created_at,
                            customer_first_name,
                            customer_last_name,
                            customer_phone_num,
                            customer_email,
                            customer_address,
                            customer_unit,
                            customer_city,
                            customer_state,
                            customer_zip,
                            customer_lat,
                            customer_long,
                            password_salt,
                            password_hashed,
                            password_algorithm,
                            referral_source,
                            role,
                            user_social_media,
                            user_access_token,
                            social_timestamp,
                            user_refresh_token,
                            mobile_access_token,
                            mobile_refresh_token,
                            social_id
                        )
                        VALUES
                        (
                        
                            \'"""+ NewUserID+ """\',
                            \'"""+ (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+ """\',
                            \'"""+ firstName+ """\',
                            \'"""+ lastName+ """\',
                            \'"""+ phone+ """\',
                            \'"""+ email+ """\',
                            \'"""+ address+ """\',
                            \'"""+ unit+ """\',
                            \'"""+ city+ """\',
                            \'"""+ state+ """\',
                            \'"""+ zip_code+ """\',
                            \'"""+ latitude+ """\',
                            \'"""+ longitude+ """\',
                            \'"""+ salt+ """\',
                            \'"""+ password+ """\',
                            \'"""+ algorithm+ """\',
                            \'"""+ referral+ """\',
                            \'"""+ role+ """\',
                            \'"""+ user_social_signup+ """\',
                            \'"""+ user_access_token+ """\',
                            DATE_ADD(now() , INTERVAL 14 DAY),
                            \'"""+ user_refresh_token+ """\',
                            \'"""+ mobile_access_token+ """\',
                            \'"""+ mobile_refresh_token+ """\',
                            \'"""+ social_id+ """\');"""
                        ]
            print(customer_insert_query[0])
            items = execute(customer_insert_query[0], "post", conn)

            if items["code"] != 281:
                items["result"] = ""
                items["code"] = 480
                items["message"] = "Error while inserting values in database"

                return items

            items["result"] = {
                "first_name": firstName,
                "last_name": lastName,
                "customer_uid": NewUserID,
                "access_token": user_access_token,
                "refresh_token": user_refresh_token,
                "access_token": mobile_access_token,
                "refresh_token": mobile_refresh_token,
                "social_id": social_id,
            }
            items["message"] = "Signup successful"
            items["code"] = 200

            print("sss-----", social_signup)

            # generate coupon for new user

            # query = ["CALL nitya.new_coupons_uid;"]
            # couponIDresponse = execute(query[0], "get", conn)
            # couponID = couponIDresponse["result"][0]["new_id"]
            # EndDate = date.today() + timedelta(days=30)
            # exp_time = str(EndDate) + " 00:00:00"

            # query = (
            #     """
            #         INSERT INTO nitya.coupons 
            #         (
            #             coupon_uid, 
            #             coupon_id, 
            #             valid, 
            #             discount_percent, 
            #             discount_amount, 
            #             discount_shipping, 
            #             expire_date, 
            #             limits, 
            #             notes, 
            #             num_used, 
            #             recurring, 
            #             email_id, 
            #             cup_business_uid, 
            #             threshold
            #         ) 
            #         VALUES 
            #         ( 
            #             \'"""+ couponID+ """\', 
            #             'NewCustomer', 
            #             'TRUE', 
            #             '0', 
            #             '0', 
            #             '5', 
            #             \'"""+ exp_time+ """\', 
            #             '1', 
            #             'Welcome Coupon', 
            #             '0', 
            #             'F', 
            #             \'"""+ email+ """\', 
            #             'null', 
            #             '0'
            #         );
            #         """
            # )
            # print(query)
            # item = execute(query, "post", conn)
            # if item["code"] != 281:
            #     item["message"] = "check sql query for coupons"
            #     item["code"] = 400
            #     return item
            # return items

        except:
            print("Error happened while Sign Up")
            if "NewUserID" in locals():
                execute(
                    """DELETE FROM customers WHERE customer_uid = '"""
                    + NewUserID
                    + """';""",
                    "post",
                    conn,
                )
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class AccountSalt(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            query = (
                """
                    SELECT password_algorithm, 
                            password_salt,
                            user_social_media 
                    FROM nitya.customers cus
                    WHERE customer_email = \'""" + email + """\';
                """
            )
            items = execute(query, "get", conn)
            print(items)
            if not items["result"]:
                items["message"] = "Email doesn't exists"
                items["code"] = 404
                return items
            if items["result"][0]["user_social_media"] != "NULL":
                items["message"] = (
                    """Social Signup exists. Use \'"""
                    + items["result"][0]["user_social_media"]
                    + """\' """
                )
                items["code"] = 401
                return items
            items["message"] = "SALT sent successfully"
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class Login(Resource):
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            password = data.get("password")
            social_id = data.get("social_id")
            signup_platform = data.get("signup_platform")
            query = (
                """
                    # CUSTOMER QUERY 1: LOGIN
                    SELECT customer_uid,
                        customer_last_name,
                        customer_first_name,
                        customer_email,
                        password_hashed,
                        email_verified,
                        user_social_media,
                        user_access_token,
                        user_refresh_token,
                        user_access_token,
                        user_refresh_token,
                        social_id
                    FROM nitya.customers c
                    WHERE customer_email = \'""" + email + """\';
                """
            )
            items = execute(query, "get", conn)
            print("Password", password)
            print(items)

            if items["code"] != 280:
                response["message"] = "Internal Server Error."
                response["code"] = 500
                return response
            elif not items["result"]:
                items["message"] = "Email Not Found. Please signup"
                items["result"] = ""
                items["code"] = 404
                return items
            else:
                print(items["result"])
                print("sc: ", items["result"][0]["user_social_media"])

                # checks if login was by social media
                if (
                    password
                    and items["result"][0]["user_social_media"] != "NULL"
                    and items["result"][0]["user_social_media"] != None
                ):
                    response["message"] = "Need to login by Social Media"
                    response["code"] = 401
                    return response

                # nothing to check
                elif (password is None and social_id is None) or (
                    password is None
                    and items["result"][0]["user_social_media"] == "NULL"
                ):
                    response["message"] = "Enter password else login from social media"
                    response["code"] = 405
                    return response

                # compare passwords if user_social_media is false
                elif (
                    items["result"][0]["user_social_media"] == "NULL"
                    or items["result"][0]["user_social_media"] == None
                ) and password is not None:

                    if items["result"][0]["password_hashed"] != password:
                        items["message"] = "Wrong password"
                        items["result"] = ""
                        items["code"] = 406
                        return items

                    if ((items["result"][0]["email_verified"]) == "0") or (
                        items["result"][0]["email_verified"] == "FALSE"
                    ):
                        response["message"] = "Account need to be verified by email."
                        response["code"] = 407
                        return response

                # compare the social_id because it never expire.
                elif (items["result"][0]["user_social_media"]) != "NULL":

                    if signup_platform != items["result"][0]["user_social_media"]:
                        items["message"] = (
                            "Wrong social media used for signup. Use '"
                            + items["result"][0]["user_social_media"]
                            + "'."
                        )
                        items["result"] = ""
                        items["code"] = 411
                        return items

                    if items["result"][0]["social_id"] != social_id:
                        print(items["result"][0]["social_id"])

                        items["message"] = "Cannot Authenticated. Social_id is invalid"
                        items["result"] = ""
                        items["code"] = 408
                        return items

                else:
                    string = " Cannot compare the password or social_id while log in. "
                    print("*" * (len(string) + 10))
                    print(string.center(len(string) + 10, "*"))
                    print("*" * (len(string) + 10))
                    response["message"] = string
                    response["code"] = 500
                    return response
                del items["result"][0]["password_hashed"]
                del items["result"][0]["email_verified"]

                query = (
                    "SELECT * from nitya.customers WHERE customer_email = '" + email + "';"
                )
                items = execute(query, "get", conn)
                items["message"] = "Authenticated successfully."
                items["code"] = 200
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class stripe_key(Resource):
    
    def get(self, desc):    
        print(desc)      
        if desc == 'NITYATEST':
            return {'publicKey': stripe_public_test_key} 
        else:             
            return {'publicKey': stripe_public_live_key} 

# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes

api.add_resource(appointments, "/api/v2/appointments")
api.add_resource(treatments, "/api/v2/treatments")
api.add_resource(FullBlog, "/api/v2/fullBlog/<string:blog_id>")
api.add_resource(TruncatedBlog, "/api/v2/truncatedBlog")
api.add_resource(
    OneCustomerAppointments, "/api/v2/oneCustomerAppointments/<string:customer_uid>"
)
api.add_resource(CreateAppointment, "/api/v2/createAppointment")
api.add_resource(AddTreatment, "/api/v2/addTreatment")
api.add_resource(AddBlog, "/api/v2/addBlog")
api.add_resource(Calendar, "/api/v2/calendar/<string:date_value>")
# api.add_resource(Calendar, "/api/v2/calendar/<string:treatment_uid>/<string:date_value>")
api.add_resource(AddContact, "/api/v2/addContact")
api.add_resource(purchaseDetails, "/api/v2/purchases")

api.add_resource(createAccount, "/api/v2/createAccount")
api.add_resource(AccountSalt, "/api/v2/AccountSalt")
api.add_resource(Login, "/api/v2/Login/")
api.add_resource(stripe_key, '/api/v2/stripe_key/<string:desc>')


# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
