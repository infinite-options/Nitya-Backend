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


RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
RDS_PORT = 3306
RDS_USER = "admin"
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

# # These statment return Day and Time in GMT
# def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
# def getNow(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")

# # These statment return Day and Time in Local Time - Not sure about PST vs PDT
def getToday(): return datetime.strftime(datetime.now(), "%Y-%m-%d")
def getNow(): return datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")

# Not sure what these statments do
# getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
# print(getToday)
# getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
# print(getNow)


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


# -- Stored Procedures start here -------------------------------------------------------------------------------


# RUN STORED PROCEDURES
def get_new_paymentID(conn):
    newPaymentQuery = execute("CALL new_payment_uid", 'get', conn)
    if newPaymentQuery['code'] == 280:
        return newPaymentQuery['result'][0]['new_id']
    return "Could not generate new payment ID", 500

def get_new_contactUID(conn):
    newPurchaseQuery = execute("CALL nitya.new_contact_uid()", 'get', conn)
    if newPurchaseQuery['code'] == 280:
        return newPurchaseQuery['result'][0]['new_id']
    return "Could not generate new contact UID", 500

# -- Queries start here -------------------------------------------------------------------------------

# QUERY 1:  FINDS ALL CUSTOMERS APPOINTMENTS
class appointments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """  
                SELECT * FROM nitya.customers, nitya.treatments, nitya.appointments
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

class OneCustomerAppointments(Resource):
    def get(self, customer_uid):
        response = {}
        items = {}
        print("appointment_uid", customer_uid)  
        try:
            conn = connect()
            # QUERY 1B:  FINDS SPECIFIC CUSTOMERS APPOINTMENTS  
            query = """
                SELECT * FROM nitya.customers, nitya.treatments, nitya.appointments
		        WHERE customer_uid = appt_customer_uid
			        AND treatment_uid = appt_treatment_uid
                    AND customer_uid = \'""" + customer_uid + """\';
                """
            items = execute(query, "get", conn)

            response["message"] = "Specific Appointment successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest("Customer Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)


# QUERY 2:  GETS ALL TREATMENTS
class treatments(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 2
            query = """  
                SELECT * FROM  nitya.treatments
                WHERE availability = "Available"; 
                """
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
            print("Received:", data)

             #  GET CUSTOMER APPOINTMENT INFO
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
           

            #  PRINT CUSTOMER APPOINTMENT INFO
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

            #  CREATE CUSTOMER APPOINTMENT UID
            # Query [0]  Get New UID
            # query = ["CALL new_refund_uid;"]
            query = ["CALL nitya.new_appointment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)
            # NewID is an Array and new_id is the first element in that array

            #  FIND EXISTING CUSTOMER UID
            query1 = (
                """ 
                    SELECT customer_uid FROM nitya.customers 
                    WHERE customer_email = \'""" + email + """\' 
                    AND   customer_phone_num = \'""" + phone_no + """\';
                """
            )
            cus_id = execute(query1, "get", conn)
            print(cus_id["result"])
            for obj in cus_id["result"]:
                NewcustomerID = obj["customer_uid"]
                print(NewcustomerID)

            print(len(cus_id["result"]))

            #  FOR NEW CUSTOMERS - CREATE NEW CUSTOMER UID AND INSERT INTO CUSTOMER TABLE
            if len(cus_id["result"]) == 0:
                query = ["CALL nitya.new_customer_uid;"]
                NewIDresponse = execute(query[0], "get", conn)
                NewcustomerID = NewIDresponse["result"][0]["new_id"]

                customer_insert_query = """
                    INSERT INTO nitya.customers
                    SET customer_uid = \'""" + NewcustomerID + """\',
                        customer_first_name = \'""" + first_name + """\',
                        customer_last_name = \'""" + last_name + """\',
                        customer_phone_num = \'""" + phone_no + """\',
                        customer_email = \'""" + email + """\'
                    """

                customer_items = execute(customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)

            #  FOR EXISTING CUSTOMERS - USE EXISTING CUSTOMER UID
            else:
                for obj in cus_id["result"]:
                    NewcustomerID = obj["customer_uid"]
                    print("customerID = ", NewcustomerID)

            #  convert to new format:  payment_time_stamp = \'''' + getNow() + '''\',

            #  INSERT INTO APPOINTMENTS TABLE
            query2 = """
                    INSERT INTO nitya.appointments
                    SET appointment_uid = \'""" + NewID + """\',
                        appt_customer_uid = \'""" + NewcustomerID + """\',
                        appt_treatment_uid = \'""" + treatment_uid + """\',
                        notes = \'""" + str(notes) + """\',
                        appt_date = \'""" + datevalue + """\',
                        appt_time = \'""" + timevalue + """\',
                        purchase_price = \'""" + purchase_price + """\',
                        purchase_date = \'""" + purchase_date + """\'
                    """
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
            print(data)
            print(message)

            new_contact_uid = get_new_contactUID(conn)
            print(new_contact_uid)
            print(getNow())

            
            query =  '''
                INSERT INTO nitya.contact
                SET contact_uid = \'''' + new_contact_uid + '''\',
                    contact_created_at = \'''' + getNow() + '''\',
                    name = \'''' + name + '''\',
                    email = \'''' + email + '''\',
                    subject = \'''' + subject + '''\',
                    message = \'''' + message + '''\'
                '''
            
            items = execute(query, "post", conn)
            print("items: ", items)
            if items["code"] == 281:
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
                 SELECT appointment_uid,customer_first_name,customer_last_name,customer_phone_num, customer_email,appt_date,appt_time,purchase_price, purchase_date,cost, appt_treatment_uid,title 
                 FROM appointments 
                 LEFT JOIN customers 
                 ON appt_customer_uid = customer_uid 
                 LEFT JOIN treatments 
                 ON appt_treatment_uid = treatment_uid; """

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

class AvailableAppointments(Resource):
    def get(self, date_value, duration):
        print("\nInside Available Appointments")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", date_value, duration)

            # CALCULATE AVAILABLE TIME SLOTS
            query = """
                    -- AVAILABLE TIME SLOTS QUERY - WORKS
                    WITH ats AS (
                    -- CALCULATE AVAILABLE TIME SLOTS
                    SELECT -- *,
                        -- ROW_NUMBER() OVER() AS row_num,
                        row_num,
                        cast(begin_datetime as time) AS begin_time,
                        cast(end_datetime as time) AS end_time
                        -- *,
                        -- TIMEDIFF(stop_time,begin_time),
                        -- IF (ISNULL(taadpa.appointment_uid) AND ISNULL(taadpa.prac_avail_uid) AND !ISNULL(days_uid), "Available", "Not Available") AS AVAILABLE
                    FROM(
                        -- GET TIME SLOTS
                        SELECT ts.*,
                            ROW_NUMBER() OVER() AS row_num,
                            TIME(ts.begin_datetime) AS ts_begin,
                            TIME(ts.end_datetime) AS ts_end,
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
                            WHERE appt_date = '""" + date_value + """') AS appt_dur
                        ON TIME(ts.begin_datetime) = appt_dur.start_time
                            OR (TIME(ts.begin_datetime) > appt_dur.start_time AND TIME(end_datetime) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM nitya.practioner_availability
                            WHERE date = '""" + date_value + """') AS pa
                        ON TIME(ts.begin_datetime) = pa.start_time_notavailable
                            OR (TIME(ts.begin_datetime) > pa.start_time_notavailable AND TIME(ts.end_datetime) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                            FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK('""" + date_value + """')) AS openhrs
                        ON TIME(ts.begin_datetime) = openhrs.morning_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.morning_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_datetime) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_datetime) > openhrs.afternoon_start_time AND TIME(ts.end_datetime) <= ADDTIME(openhrs.afternoon_end_time,"0:29")) 
                        )AS taadpa
                    WHERE ISNULL(taadpa.appointment_uid) 
                        AND ISNULL(taadpa.prac_avail_uid)
                        AND !ISNULL(days_uid)
                    )

                    SELECT *
                    FROM (
                        SELECT -- *,
                            row_num,
                            DATE_FORMAT(begin_time, '%T') AS "begin_time",
                            CASE
                                WHEN ISNULL(row_num_hr) THEN "0:29:59"
                                WHEN ISNULL(row_num_hrhalf) THEN "0:59:59"
                                WHEN ISNULL(row_num_twohr) THEN "1:29:59"
                                ELSE "1:59:59"
                            END AS available_duration
                        FROM (
                            SELECT *
                            FROM ats
                            LEFT JOIN (
                                SELECT 	
                                    row_num as row_num_hr,
                                    begin_time AS begin_time_hr,
                                    end_time AS end_time_hr
                                FROM ats) AS ats1
                            ON ats.row_num + 1 = ats1.row_num_hr
                            LEFT JOIN (
                                SELECT 	
                                    row_num as row_num_hrhalf,
                                    begin_time AS begin_time_hrhalf,
                                    end_time AS end_time_hrhalf
                                FROM ats) AS ats2
                            ON ats.row_num + 2 = ats2.row_num_hrhalf
                            LEFT JOIN (
                                SELECT 	
                                    row_num as row_num_twohr,
                                    begin_time AS begin_time_twohr,
                                    end_time AS end_time_twohr
                                FROM ats) AS ats3
                            ON ats.row_num + 3 = ats3.row_num_twohr) AS atss) AS atsss
                    WHERE '""" + duration + """' <= available_duration;
                    """

            available_times = execute(query, 'get', conn)
            print("Available Times: ", str(available_times['result']))
            print("Number of time slots: ", len(available_times['result']))
            # print("Available Times: ", str(available_times['result'][0]["appt_start"]))

            return available_times
        
        except:
            raise BadRequest('Available Time Request failed, please try again later.')
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
                            WHERE appt_date = '""" + date_value + """') AS appt_dur
                        ON TIME(ts.begin_time) = appt_dur.start_time
                            OR (TIME(ts.begin_time) > appt_dur.start_time AND TIME(ts.stop_time) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM nitya.practioner_availability
                            WHERE date = '""" + date_value + """') AS pa
                        ON TIME(ts.begin_time) = pa.start_time_notavailable
                            OR (TIME(ts.begin_time) > pa.start_time_notavailable AND TIME(ts.stop_time) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                                -- ADDTIME(morning_start_time, "0:29"),
                                -- if(morning_start_time = "9:00:00","Y","N")
                            FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK('""" + date_value + """')) AS openhrs
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

            # d = datetime.strptime('0:29:59', '%H:%M:%S' )
            # print(d, type(d))
            # times = []

            # # Two things to take into account:
            # # 1.  The duration calculation
            # #     Duration is met if end time - start time >= duration
            # # 2.  The contiguous relationships between times
            # #     Times are contiguous if end time = next start time

            # n = 0
            # m = n
            # time_zero = datetime.strptime('00:00:00', '%H:%M:%S')
            # print(time_zero, type(time_zero))
            # while n < len(available_times['result']):
            #     # s = datetime.strptime(available_times['result'][n]["appt_start"], '%H:%M:%S' ).time()
            #     # e = datetime.strptime(available_times['result'][n]["appt_end"], '%H:%M:%S' ).time()
            #     # print(s)
            #     # print(e)
            #     # DURATION TEST
            #     while m < len(available_times['result']):
            #         print(n)
            #         print(m)
            #         s = datetime.strptime(available_times['result'][n]["appt_start"], '%H:%M:%S' )
            #         e = datetime.strptime(available_times['result'][m]["appt_end"], '%H:%M:%S' )
            #         print(s, type(s))
            #         print(e, type(e))
            #         print((s - time_zero).time())
            #         # print((s - time_zero + d).time())
            #         # if (s -time_zero + d).time() <= e:
            #         #     times.append(s).time()
            #         #     continue
            #     m = m + 1
            # n = n + 1
            # print(times)


            # for appt in available_times['result']:
            #     s = datetime.strptime(appt['appt_start'], '%H:%M:%S' ).time()
            #     e = datetime.strptime(appt['appt_end'], '%H:%M:%S' ).time()
            #     if s + d <= e:
            #         times.append(appt['appt_start'])

            # print(times)



            # n = 0
            # while n < len(available_times['result']):
                



            # 

            # d = datetime.strptime('0:30:00', '%H:%M:%S' ).time()
            # print(d, type(d))
            # # duration = datetime(0:60:00)
            # for appt in available_times['result']:
            #     print(appt)
            #     print(appt['appt_start'], type(appt['appt_start']))
            #     print(appt['appt_end'], type(appt['appt_end']))
            #     # x = appt['appt_end'] - appt['appt_start']
            #     # print(x, type(x))
            #     s = datetime.strptime(appt['appt_end'], '%H:%M:%S' ).time()
            #     e = datetime.strptime(appt['appt_end'], '%H:%M:%S' ).time()
                
            #     print(s, type(s))
            
                # print(datetime.strptime(appt['appt_end']))
                #  - datetime.strptime(appt['appt_start']))
        
        except:
            raise BadRequest('Available Time Request failed, please try again later.')
        finally:
            disconnect(conn)


# ACCOUNT QUERIES
class findCustomerUID(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            phone = data["phone_num"]
            email = data["email"]
            query = (
                """
                    # QUERY 5
                    # GET CUSTOMER UID FROM PHONE NUMBER OR EMAIL
                    SELECT customer_uid,
                        customer_phone_num,
                        customer_email
                    FROM nitya.customers 
                    WHERE customer_phone_num = \'""" + phone + """\'
                        OR customer_email = \'""" + email + """\';
                """
            )
            items = execute(query, "get", conn)
            print(items)
            if not items["result"]:
                items["message"] = "Email and Phone Number do not exist"
                items["code"] = 404
                return items
            items["message"] = "Customer Found"
            items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

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
api.add_resource(AvailableAppointments, "/api/v2/availableAppointments/<string:date_value>/<string:duration>")
api.add_resource(AddContact, "/api/v2/addContact")
api.add_resource(purchaseDetails, "/api/v2/purchases")

api.add_resource(findCustomerUID, "/api/v2/findCustomer")
api.add_resource(createAccount, "/api/v2/createAccount")
api.add_resource(AccountSalt, "/api/v2/AccountSalt")
api.add_resource(Login, "/api/v2/Login/")
api.add_resource(stripe_key, '/api/v2/stripe_key/<string:desc>')


# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
