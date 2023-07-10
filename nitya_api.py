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

from dotenv import load_dotenv
import os
import boto3
import json
from datetime import date, datetime

import stripe

from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message

# used for serializer email and error handling
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
# from flask_cors import CORS

from werkzeug.exceptions import BadRequest, InternalServerError

#  NEED TO SOLVE THIS
# from NotificationHub import Notification
# from NotificationHub import NotificationHub

from decimal import Decimal
from datetime import datetime, date
from hashlib import sha512

# BING API KEY
# Import Bing API key into bing_api_key.py

#  NEED TO SOLVE THIS
# from env_keys import BING_API_KEY, RDS_PW
from dotenv import load_dotenv

import sys
import json
import pytz
import pymysql
import requests
from fuzzywuzzy import fuzz

RDS_HOST = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
RDS_PORT = 3306
RDS_USER = "admin"
RDS_DB = "nitya"

SCOPES = "https://www.googleapis.com/auth/calendar"
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "nitya-ayurveda"
# app = Flask(__name__)
app = Flask(__name__, template_folder="assets")

load_dotenv()

# --------------- Stripe Variables ------------------
# these key are using for testing. Customer should use their stripe account's keys instead


# STRIPE AND PAYPAL KEYS
paypal_secret_test_key = os.getenv("paypal_secret_key_test")
paypal_secret_live_key = os.getenv("paypal_secret_key_live")

paypal_client_test_key = os.getenv("paypal_client_test_key")
paypal_client_live_key = os.getenv("paypal_client_live_key")

stripe_public_test_key = os.getenv("stripe_public_test_key")
stripe_secret_test_key = os.getenv("stripe_secret_test_key")

stripe_public_live_key = os.getenv("stripe_public_live_key")
stripe_secret_live_key = os.getenv("stripe_secret_live_key")

stripe.api_key = stripe_secret_test_key

# use below for local testing
# stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3""


# CORS(app)
CORS(app, resources={r'/api/*': {'origins': '*'}})

# --------------- Mail Variables ------------------
# Mail username and password loaded in .env file
app.config['MAIL_USERNAME'] = os.getenv('SUPPORT_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('SUPPORT_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')


# Setting for mydomain.com
app.config["MAIL_SERVER"] = "smtp.mydomain.com"
app.config["MAIL_PORT"] = 465

# Setting for gmail
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465


app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True


# Set this to false when deploying to live application
app.config["DEBUG"] = True
# app.config["DEBUG"] = False

app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY")

mail = Mail(app)

# API
api = Api(app)

# convert to UTC time zone when testing in local time zone
utc = pytz.utc

# # These statment return Day and Time in GMT
# def getToday(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d")
# def getNow(): return datetime.strftime(datetime.now(utc), "%Y-%m-%d %H:%M:%S")

# # These statment return Day and Time in Local Time - Not sure about PST vs PDT


def getToday():
    return datetime.strftime(datetime.now(), "%Y-%m-%d")


def getNow():
    return datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")


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


s3 = boto3.client("s3")

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('nitya-images')
BUCKET_NAME = "nitya-images"
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])


# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.getenv("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.getenv("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

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
            if cmd == "get":
                result = cur.fetchall()
                response["message"] = "Successfully executed SQL query."
                # Return status code of 280 for successful GET request
                response["code"] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response["result"] = result
            elif cmd == "post":
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
    newPaymentQuery = execute("CALL new_payment_uid", "get", conn)
    if newPaymentQuery["code"] == 280:
        return newPaymentQuery["result"][0]["new_id"]
    return "Could not generate new payment ID", 500


def get_new_contactUID(conn):
    newPurchaseQuery = execute("CALL nitya.new_contact_uid()", "get", conn)
    if newPurchaseQuery["code"] == 280:
        return newPurchaseQuery["result"][0]["new_id"]
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
            raise BadRequest(
                "Appointments Request failed, please try again later.")
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
            query = (
                """
                SELECT * FROM nitya.customers, nitya.treatments, nitya.appointments
		        WHERE customer_uid = appt_customer_uid
			        AND treatment_uid = appt_treatment_uid
                    AND customer_uid = \'"""
                + customer_uid
                + """\';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Appointment successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest(
                "Customer Appointments Request failed, please try again later."
            )
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
                WHERE availability = "Available"
                ORDER BY category, display_order;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)

        # http://localhost:4000/api/v2/treatments

# QUERY 2:  GETS ALL TREATMENTS


class availability(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 2
            query = """
                SELECT * FROM  nitya.days;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)


class updateAvailability(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()

            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            days = data['days']
            print('days', days)

            for day in days:
                print('day', day[0]['id'])
                query = (
                    """UPDATE nitya.days
                            SET
                                morning_start_time = \'""" + day[0]['morning_start_time'] + """\',
                                morning_end_time = \'""" + day[0]['morning_end_time'] + """\',
                                afternoon_start_time = \'""" + day[0]['afternoon_start_time'] + """\',
                                afternoon_end_time = \'""" + day[0]['afternoon_end_time'] + """\'
                            WHERE days_uid = \'""" + day[0]['id'] + """\'; """
                )

                items = execute(query, "post", conn)
                print(items)

            if items["code"] == 281:
                response["message"] = "Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)


class unavailability(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 2
            query = """
                SELECT * FROM  nitya.practioner_availability;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)


class updateUnavailability(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()

            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            date = data["date"]
            start_time_notavailable = data["start_time_notavailable"]
            end_time_notavailable = data["end_time_notavailable"]

            query_get = """
                SELECT * FROM  nitya.practioner_availability
                ORDER by prac_avail_uid;
                """
            # The query is executed here
            items_get = execute(query_get, "get", conn)

            result = int(items_get['result'][-1]['number'])+1
            print(result)
            # QUERY 2
            query = ["CALL nitya.new_practioner_availability_uid;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO nitya.practioner_availability
                    SET prac_avail_uid  = \'"""
                + NewID
                + """\',
                        number = \'"""
                + str(result)
                + """\',
                        date = \'"""
                + date
                + """\',
                        start_time_notavailable = \'"""
                + start_time_notavailable
                + """\',
                        end_time_notavailable = \'"""
                + end_time_notavailable
                + """\';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)

    def put(self):
        print("\nInside UPDATE Inventory")
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            id = data["id"]
            date = data["date"]
            start_time_notavailable = data["start_time_notavailable"]
            end_time_notavailable = data["end_time_notavailable"]

            query = (""" UPDATE nitya.practioner_availability
                        SET 
                            date = \'""" + date + """\',
                            start_time_notavailable = \'""" + start_time_notavailable + """\',
                            end_time_notavailable = \'""" + end_time_notavailable + """\'
                        WHERE prac_avail_uid = \'""" + id + """\';
                    """)

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)


class deleteUnavailability(Resource):
    def post(self, id):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            query = (
                """
                    DELETE FROM nitya.practioner_availability
                   WHERE prac_avail_uid = '"""
                + id
                + """';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
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
            print("Received:", data)

            blogCategory = data["blogCategory"]
            # print(blogCategory)
            blogTitle = data["blogTitle"]
            # print(blogTitle)
            slug = data["slug"]
            # print(slug)
            postedOn = data["postedOn"]
            # print(postedOn)
            author = data["author"]
            # print(author)
            blogImage = data["blogImage"]
            print(blogImage)
            blogSummary = data["blogSummary"]
            # print(blogSummary)
            blogText = data["blogText"]
            # print(blogText)
            print("Data Received")

            query = ["CALL nitya.new_blog_uid;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO nitya.blog
                    SET blog_uid  = \'"""
                + NewID
                + """\',
                        blogCategory = \'"""
                + blogCategory
                + """\',
                        blogTitle = \'"""
                + blogTitle
                + """\',
                        blogStatus = 'ACTIVE',
                        slug = \'"""
                + slug
                + """\',
                        postedOn = \'"""
                + postedOn
                + """\',
                        author = \'"""
                + author
                + """\',
                        blogImage = \'"""
                + blogImage
                + """\',
                        blogSummary = \'"""
                + blogSummary
                + """\',
                        blogText = \'"""
                + blogText
                + """\';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Blog Post successful"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UploadImage(Resource):
    def post(self):
        try:
            print("in Upload Image")
            item_photo = request.files.get("item_photo")
            print(item_photo)
            uid = request.form.get("filename")
            print(uid)
            bucket = "nitya-images"
            TimeStamp_test = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            print(TimeStamp_test)
            key = "blogs/" + str(uid) + "_" + TimeStamp_test
            print(key)

            filename = (
                "https://s3-us-west-1.amazonaws.com/" +
                str(bucket) + "/" + str(key)
            )

            upload_file = s3.put_object(
                Bucket=bucket,
                Body=item_photo,
                Key=key,
                ACL="public-read",
                ContentType="image/jpeg",
            )
            return filename

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            print("image uploaded!")


class UploadVideo(Resource):
    def post(self):
        try:
            item_video = request.files.get("item_video")
            bucket = "nitya-images"
            uid = request.form.get("filename")
            TimeStamp_test = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            print(TimeStamp_test)
            key = "blogsVideos/" + str(uid) + "_" + TimeStamp_test
            print(key)

            filename = (
                "https://s3-us-west-1.amazonaws.com/" +
                str(bucket) + "/" + str(key)
            )

            # s3.upload_file(Bucket=bucket,
            #                Body=item_video,
            #                Key=key)
            upload_file = s3.put_object(
                Bucket=bucket,
                Body=item_video,
                Key=key,
                ACL="public-read",
                ContentType="video/mp4",
            )
            print("Upload Successful")
            return filename
        except FileNotFoundError:
            print("The file was not found")
            return False


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
                    WHERE blog_uid = \'"""
                + blog_id
                + """\'
                    AND blogStatus != 'DELETED';
                """
            )
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest(
                "Full Blog Request failed, please try again later.")
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
                    SELECT blog_uid, blogCategory, blogTitle, slug, postedOn, author, blogImage, blogSummary, LEFT(blogText, 1200) AS blogText
                    FROM nitya.blog
                    WHERE blogStatus != 'DELETED'
                    ORDER BY postedOn DESC;
                    """
            items = execute(query, "get", conn)

            response["message"] = "Specific Blog successful"
            response["result"] = items["result"]
            return response, 200
        except:
            raise BadRequest(
                "Specific Blog Request failed, please try again later.")
        finally:
            disconnect(conn)


class DeleteBlog(Resource):
    def post(self, blog_id):
        print("\nInside Delete")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block")
            print("Received:", blog_id)

            query = (
                """
                    UPDATE nitya.blog
                    SET blogStatus = 'DELETED'
                    WHERE blog_uid = \'"""
                + blog_id
                + """\';
                    """
            )

            products = execute(query, "post", conn)
            print("Back in class")
            print(products)
            return products["code"]

        except:
            raise BadRequest("Delete Request failed, please try again later.")
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
            mode = data["mode"]
            gender = data["gender"]
            age = data["age"]

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
            print("age", age)

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
                    WHERE customer_email = \'"""
                + email
                + """\'
                    AND   customer_phone_num = \'"""
                + phone_no
                + """\';
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

                customer_insert_query = (
                    """
                    INSERT INTO nitya.customers
                    SET customer_uid = \'"""
                    + NewcustomerID
                    + """\',
                        customer_first_name = \'"""
                    + first_name
                    + """\',
                        customer_last_name = \'"""
                    + last_name
                    + """\',
                        customer_phone_num = \'"""
                    + phone_no
                    + """\',
                        customer_email = \'"""
                    + email
                    + """\'
                    """
                )

                customer_items = execute(customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)

            #  FOR EXISTING CUSTOMERS - USE EXISTING CUSTOMER UID
            else:
                for obj in cus_id["result"]:
                    NewcustomerID = obj["customer_uid"]
                    print("customerID = ", NewcustomerID)

            #  convert to new format:  payment_time_stamp = \'''' + getNow() + '''\',

            #  INSERT INTO APPOINTMENTS TABLE
            query2 = (
                """
                    INSERT INTO nitya.appointments
                    SET appointment_uid = \'"""
                + NewID
                + """\',
                        appt_customer_uid = \'"""
                + NewcustomerID
                + """\',
                        appt_treatment_uid = \'"""
                + treatment_uid
                + """\',
                        notes = \'"""
                + str(notes).replace("'", "''")
                + """\',
                        appt_date = \'"""
                + datevalue
                + """\',
                        appt_time = \'"""
                + timevalue
                + """\',
                        purchase_price = \'"""
                + purchase_price
                + """\',
                        purchase_date = \'"""
                + purchase_date
                + """\',
                        mode = \'"""
                + mode
                + """\',
                        gender = \'"""
                + gender
                + """\',
                        age = \'"""
                + age
                + """\'
                    """
            )
            items = execute(query2, "post", conn)
            query3 = (
                """
                    SELECT title FROM nitya.treatments
                    WHERE treatment_uid = \'"""
                + treatment_uid
                + """\';
                """
            )
            treatment = execute(query3, "get", conn)
            print(treatment['result'][0]['title'])
            # Send receipt emails
            name = first_name + " " + last_name
            age = age
            gender = gender
            message = treatment['result'][0]['title'] + "," + \
                purchase_price + "," + datevalue + "," + timevalue
            print(name)
            print('os.environ.get("SUPPORT_EMAIL")',
                  os.environ.get("SUPPORT_EMAIL"))
            response["message"] = "Appointments Post successful"
            response["result"] = items
            print('response', response)
            SendEmail.get(self, name, age, gender,
                          mode, str(notes), email, phone_no, message)

            return response, 200
        except:
            raise BadRequest("Request failed app, please try again later.")
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
            print("Received:", data)

            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            availability = data["availability"]
            duration = data["duration"]
            treatment_notes = data["treatment_notes"]
            display_order = data["display_order"]
            image_url = data["image_url"]

            print("treatment_notes:", treatment_notes)
            print("display_order:", display_order)
            

            query = ["CALL nitya.new_treatment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)

            query = (
                """
                    INSERT INTO nitya.treatments
                    SET treatment_uid = \'"""
                + NewID
                + """\',
                        title = \'"""
                + title
                + """\',
                        category = \'"""
                + category
                + """\',
                        description = \'"""
                + description
                + """\',
                        cost = \'"""
                + cost
                + """\',
                        availability = \'"""
                + availability
                + """\',
                        duration = \'"""
                + duration
                + """\',

                        treatment_notes = \'"""
                + treatment_notes
                + """\',
                        display_order = \'"""
                + display_order
                + """\',


                        image_url = \'"""
                + image_url
                + """\';
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


class UpdateTreatment(Resource):
    def post(self):
        print("\nInside UPDATE Treatment")
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            id = data["treatment_uid"]
            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            availability = data["availability"]
            duration = data["duration"]
            treatment_notes = data["treatment_notes"]
            display_order = data["display_order"]
            image_url = data["image_url"]

            print("Update ID = ", id)

            query = (
                """
                    UPDATE nitya.treatments
                    SET title = \'"""
                + title
                + """\',
                        category = \'"""
                + category
                + """\',
                        description = \'"""
                + description
                + """\',
                        cost = \'"""
                + cost
                + """\',
                        availability = \'"""
                + availability
                + """\',
                        duration = \'"""
                + duration
                + """\',

                        treatment_notes = \'"""
                + treatment_notes
                + """\',
                        display_order = \'"""
                + display_order
                + """\',


                        image_url = \'"""
                + image_url
                + """\'
                
                WHERE treatment_uid = \'"""
                + id
                + """\'
                    """
            )







            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
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
            phone = data["phone"]
            email = data["email"]
            subject = data["subject"]
            message = data["message"]
            print(data)
            print(message)

            new_contact_uid = get_new_contactUID(conn)
            print(new_contact_uid)
            print(getNow())

            query = (
                """
                INSERT INTO nitya.contact
                SET contact_uid = \'"""
                + new_contact_uid
                + """\',
                    contact_created_at = \'"""
                + getNow()
                + """\',
                    name = \'"""
                + name
                + """\',
                    phone = \'"""
                + phone
                + """\',
                    email = \'"""
                + email
                + """\',
                    subject = \'"""
                + subject
                + """\',
                    message = \'"""
                + message
                + """\'
                """
            )

            items = execute(query, "post", conn)
            print("items: ", items)

            # Send receipt emails
            # phone = message
            SendEmailNewGet.get(self, name, email,
                                str(phone), subject, message)

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
    def get(self, date_value, duration, mode):
        print("\nInside Available Appointments")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", date_value, duration, mode)

            # CALCULATE AVAILABLE TIME SLOTS
            query = (
                """
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
                        SELECT ROW_NUMBER() OVER() AS row_num,
                            ts.begin_datetime,
                            ts.end_datetime,
                            appt_dur.appointment_uid,
                            pa.prac_avail_uid,
                            openhrs.days_uid
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
                            WHERE appt_date = '"""
                + date_value
                + """') AS appt_dur
                        ON TIME(ts.begin_datetime) = appt_dur.start_time
                            OR (TIME(ts.begin_datetime) > appt_dur.start_time AND TIME(end_datetime) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT prac_avail_uid,
                                start_time_notavailable,
                                end_time_notavailable
                            FROM nitya.practioner_availability
                            WHERE date = '"""
                + date_value
                + """') AS pa
                        ON TIME(ts.begin_datetime) = pa.start_time_notavailable
                            OR (TIME(ts.begin_datetime) > pa.start_time_notavailable AND TIME(ts.end_datetime) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT days_uid,
                                morning_start_time,
                                morning_end_time,
                                afternoon_start_time,
                                afternoon_end_time
                            FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK('"""
                + date_value
                + """') AND hoursMode = '"""
                + mode
                + """') AS openhrs
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
                    WHERE '"""
                + duration
                + """' <= available_duration;
                    """
            )

            available_times = execute(query, "get", conn)
            print("Available Times: ", str(available_times["result"]))
            print("Number of time slots: ", len(available_times["result"]))
            # print("Available Times: ", str(available_times['result'][0]["appt_start"]))

            return available_times

        except:
            raise BadRequest(
                "Available Time Request failed, please try again later.")
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
            query = (
                """
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
                            WHERE appt_date = '"""
                + date_value
                + """') AS appt_dur
                        ON TIME(ts.begin_time) = appt_dur.start_time
                            OR (TIME(ts.begin_time) > appt_dur.start_time AND TIME(ts.stop_time) <= ADDTIME(appt_dur.end_time,"0:29"))
                        -- GET PRACTIONER AVAILABILITY
                        LEFT JOIN (
                            SELECT *
                            FROM nitya.practioner_availability
                            WHERE date = '"""
                + date_value
                + """') AS pa
                        ON TIME(ts.begin_time) = pa.start_time_notavailable
                            OR (TIME(ts.begin_time) > pa.start_time_notavailable AND TIME(ts.stop_time) <= ADDTIME(pa.end_time_notavailable,"0:29"))
                        -- GET OPEN HOURS
                        LEFT JOIN (
                            SELECT *
                                -- ADDTIME(morning_start_time, "0:29"),
                                -- if(morning_start_time = "9:00:00","Y","N")
                            FROM nitya.days
                            WHERE dayofweek = DAYOFWEEK('"""
                + date_value
                + """')) AS openhrs
                        ON TIME(ts.begin_time) = openhrs.morning_start_time
                            OR (TIME(ts.begin_time) > openhrs.morning_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.morning_end_time,"0:29"))
                            OR TIME(ts.begin_time) = openhrs.afternoon_start_time
                            OR (TIME(ts.begin_time) > openhrs.afternoon_start_time AND TIME(ts.stop_time) <= ADDTIME(openhrs.afternoon_end_time,"0:29"))
                        )AS taadpa
                    WHERE ISNULL(taadpa.appointment_uid)
                        AND ISNULL(taadpa.prac_avail_uid)
                        AND !ISNULL(days_uid)
                    """
            )

            available_times = execute(query, "get", conn)
            print("Available Times: ", str(available_times["result"]))
            print("Number of time slots: ", len(available_times["result"]))
            print("Available Times: ", str(
                available_times["result"][0]["appt_start"]))

            return available_times["result"]

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
            raise BadRequest(
                "Available Time Request failed, please try again later.")
        finally:
            disconnect(conn)


class CustomerToken(Resource):
    def get(self, customer_uid=None):
        print("In customertoken")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None

            query = (
                """SELECT customer_uid
                                , customer_email
                                , user_access_token
                                , user_refresh_token
                        FROM
                        customers WHERE customer_uid = \'"""
                + customer_uid
                + """\';"""
            )

            items = execute(query, "get", conn)
            print(items)
            response["message"] = "successful"
            response["customer_email"] = items["result"][0]["customer_email"]
            response["user_access_token"] = items["result"][0]["user_access_token"]
            response["user_refresh_token"] = items["result"][0]["user_refresh_token"]

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UpdateAccessToken(Resource):
    def post(self, customer_uid=None):
        print("In customertoken")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None
            data = request.get_json(force=True)
            user_access_token = data["user_access_token"]

            execute(
                """UPDATE customers
                       SET user_access_token = \'"""
                + user_access_token
                + """\'
                       WHERE customer_uid = \'"""
                + customer_uid
                + """\';
                        """,
                "post",
                conn,
            )

            # query = """UPDATE ta_people
            #            SET
            #            ta_google_auth_token = \'""" + ta_google_auth_token + """\'
            #            WHERE ta_unique_id = \'""" + ta_id + """\';"""

            # items =
            # print(items)
            response["message"] = "successful"
            # response['ta_google_auth_token'] = items['result'][0]['ta_google_auth_token']

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GoogleCalenderEvents(Resource):
    def post(self, customer_uid, start, end):
        print("In Google Calender Events")
        try:
            conn = connect()
            # data = request.get_json(force=True)
            print(customer_uid, start, end)
            timestamp = getNow()
            # customer_uid = data["id"]
            # start = data["start"]
            # end = data["end"]

            items = execute(
                """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
                + customer_uid
                + """\'""",
                "get",
                conn,
            )

            if len(items["result"]) == 0:
                return "No such user exists"
            print("items", items)
            if (
                items["result"][0]["access_expires_in"] == None
                or items["result"][0]["social_timestamp"] == None
            ):
                f = open(
                    "credentials.json",
                )
                print("in if")
                data = json.load(f)
                client_id = data["web"]["client_id"]
                client_secret = data["web"]["client_secret"]
                refresh_token = items["result"][0]["google_refresh_token"]
                print("in if", data)
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items["result"][0]["google_refresh_token"],
                }
                print("in if", params)
                authorization_url = "https://accounts.google.com/o/oauth2/token"
                r = requests.post(authorization_url, data=params)
                auth_token = ""
                if r.ok:
                    auth_token = r.json()["access_token"]
                expires_in = r.json()["expires_in"]
                print("in if", expires_in)
                execute(
                    """UPDATE customers SET
                                user_access_token = \'"""
                    + str(auth_token)
                    + """\'
                                , social_timestamp = \'"""
                    + str(timestamp)
                    + """\'
                                , access_expires_in = \'"""
                    + str(expires_in)
                    + """\'
                                WHERE customer_uid = \'"""
                    + customer_uid
                    + """\';""",
                    "post",
                    conn,
                )
                items = execute(
                    """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
                    + customer_uid
                    + """\'""",
                    "get",
                    conn,
                )
                print(items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&"
                timeMaxMin = "timeMax=" + end + "&timeMin=" + start
                url = baseUri + timeMaxMin
                bearerString = "Bearer " + \
                    items["result"][0]["user_access_token"]
                headers = {"Authorization": bearerString,
                           "Accept": "application/json"}
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                calendars = response.json().get("items")
                return calendars

            else:
                print("in else")
                access_issue_min = int(
                    items["result"][0]["access_expires_in"]) / 60
                print("in else", access_issue_min)
                print("in else", items["result"][0]["social_timestamp"])
                social_timestamp = datetime.strptime(
                    items["result"][0]["social_timestamp"], "%Y-%m-%d %H:%M:%S"
                )
                print("in else", social_timestamp)

                timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                print("in else", timestamp)
                diff = (timestamp - social_timestamp).total_seconds() / 60
                print("in else", diff)
                if int(diff) > int(access_issue_min):
                    print("in else", diff)
                    f = open(
                        "credentials.json",
                    )
                    data = json.load(f)
                    client_id = data["web"]["client_id"]
                    client_secret = data["web"]["client_secret"]
                    refresh_token = items["result"][0]["google_refresh_token"]
                    print("in else data", data)
                    params = {
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": items["result"][0]["google_refresh_token"],
                    }
                    print("in else", params)
                    authorization_url = "https://accounts.google.com/o/oauth2/token"
                    r = requests.post(authorization_url, data=params)
                    print("in else", r)
                    auth_token = ""
                    if r.ok:
                        auth_token = r.json()["access_token"]
                    expires_in = r.json()["expires_in"]
                    print("in else", expires_in)
                    execute(
                        """UPDATE customers SET
                                    user_access_token = \'"""
                        + str(auth_token)
                        + """\'
                                    , social_timestamp = \'"""
                        + str(timestamp)
                        + """\'
                                    , access_expires_in = \'"""
                        + str(expires_in)
                        + """\'
                                    WHERE customer_uid = \'"""
                        + customer_uid
                        + """\';""",
                        "post",
                        conn,
                    )

                items = execute(
                    """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
                    + customer_uid
                    + """\'""",
                    "get",
                    conn,
                )
                print("items2", items)
                baseUri = "https://www.googleapis.com/calendar/v3/calendars/primary/events?orderBy=startTime&singleEvents=true&"
                print("items2", baseUri)
                timeMaxMin = "timeMax=" + end + "&timeMin=" + start
                print(timeMaxMin)
                url = baseUri + timeMaxMin
                print(url)
                bearerString = "Bearer " + \
                    items["result"][0]["user_access_token"]
                print(bearerString)
                headers = {"Authorization": bearerString,
                           "Accept": "application/json"}
                print(headers)
                response = requests.get(url, headers=headers)

                print(response)

                response.raise_for_status()
                calendars = response.json().get("items")
                return calendars

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


def sendEmail2(recipient, subject, body):
    print('in sendemail2')
    with app.app_context():
        msg = Message(
            sender="support@nityaayurveda.com",
            recipients=recipient,
            subject=subject,
            body=body
        )
        print(msg)
        mail.send(msg)
        print('after mail send')


app.sendEmail2 = sendEmail2


class SendEmailCRON_CLASS(Resource):

    def get(self):
        print("In Send EMail get")
        try:
            conn = connect()

            # # Send email to Client
            # msg = Message(
            #     subject="Daily Email Check!",
            #     sender="support@nityaayurveda.com",
            #     recipients=["anu.sandhu7893@gmail.com"],
            # )
            # msg.body = (
            #     "Nitya Ayurveda Email Send is working. If you don't receive this email daily, something is wrong"
            # )
            # print(msg.body)
            # mail.send(msg)
            recipient = ["anu.sandhu7893@gmail.com"]
            subject = "Daily Email Check!"
            body = (
                "Nitya Ayurveda Email Send is working. If you don't receive this email daily, something is wrong")
            # mail.send(msg)
            sendEmail2(recipient, subject, body)

            return "Email Sent", 200

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


def SendEmailCRON():
    print("In Send EMail get")
    from flask_mail import Mail, Message
    try:
        conn = connect()
        print('here after connect')

        recipient = ["Lmarathay@yahoo.com",
                     "pmarathay@gmail.com", "anu.sandhu7893@gmail.com"]
        print(recipient)
        subject = "Daily Email Check!"
        print(subject)
        body = (
            "Nitya Ayurveda Email Send is working. If you don't receive this email daily, something is wrong"
        )
        print(body)
        # mail.send(msg)
        sendEmail2(recipient, subject, body)

        print('here after mail send')

        return "Email Sent", 200

    except:
        raise BadRequest("Email didnt send something is wrong.")
    finally:
        disconnect(conn)

# SEND EMAIL


class SendEmailPaymentIntent(Resource):
    def __call__(self):
        print("In SendEmailPaymentIntent")

    def post(self):
        print("In SendEmailPaymentIntent")
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            name = data["name"]
            phone = data["phone"]
            email = data["email"]
            message = data["message"]
            error = data['error']
            endpoint_call = data['endpoint_call']
            jsonObject_sent = data['jsonObject_sent']
            print("first email sent")
            print(name, email, phone, message)
            # Send email to Host
            msg = Message(
                "Payment Intent Error",
                sender="support@nityaayurveda.com",
                recipients=["pmarathay@gmail.com", "anu.sandhu7893@gmail.com"],
            )
            msg.body = (
                "Hi !\n\n"
                "Payment intent failed For the below customer \n"
                "Here are the particulars:\n"
                "Name:      " + name + "\n"
                "Email:     " + email + "\n"
                "Phone:     " + str(phone) + "\n"
                "Message:   " + message + "\n"
                "Error:     " + error + "\n"
                "Error occured at this point:" + endpoint_call + "\n"
                "JSON Object we sent:" + jsonObject_sent + "\n"
                "Thank you - Nitya Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            mail.send(msg)
            print('after mail send')

            return 'Email Sent', 200

        except:
            raise BadRequest("Request failed mail, please try again later.")
        finally:
            disconnect(conn)


class SendEmailNewGet(Resource):
    def __call__(self):
        print("In SendEmailNewGet")

    def get(self, name, email, phone, subject, message):
        print("In SendEmailNewGet")
        response = {}
        try:
            conn = connect()

            print("first email sent")
            print(name, email, phone, subject, message)
            # Send email to Host
            msg = Message(
                "New Email from Website!",
                sender="support@nityaayurveda.com",
                recipients=["Lmarathay@yahoo.com", "pmarathay@gmail.com"],
            )
            msg.body = (
                "Hi !\n\n"
                "You just got an email from your website! \n"
                "Here are the particulars:\n"
                "Name:      " + name + "\n"
                "Email:     " + email + "\n"
                "Phone:     " + str(phone) + "\n"
                "Subject:   " + subject + "\n"
                "Message:   " + message + "\n"
                "Thank you - Nitya Ayurveda\n\n"
            )

            # print('msg-bd----', msg.body)
            mail.send(msg)
            print('after mail send')

            # Send email to Sender
            msg2 = Message(
                "New Email from Nitya Ayurveda!",
                sender="support@nityaayurveda.com",
                recipients=[email],
            )
            msg2.body = (
                "Hi !\n\n"
                "Thanks for your email! \n"
                "Here are the particulars we sent:\n"
                "Name:      " + name + "\n"
                "Email:     " + email + "\n"
                "Phone:     " + str(phone) + "\n"
                "Subject:   " + subject + "\n"
                "Message:   " + message + "\n"
                "Thank you - Nitya Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            mail.send(msg2)
            print('after mail send')

            return 'Email Sent', 200

        except:
            raise BadRequest("Request failed mail, please try again later.")
        finally:
            disconnect(conn)


class SendEmail(Resource):
    def __call__(self):
        print("In SendEmail")

    def get(self, name, age, gender, mode, notes, email, phone, subject):
        print("In Send EMail get")
        response = {}
        try:
            conn = connect()
            subject = subject.split(',')

            month_num = subject[2][5:7]
            datetime_object1 = datetime.strptime(month_num, "%m")
            month_name = datetime_object1.strftime("%B")

            datetime_object2 = datetime.strptime(subject[2], "%Y-%m-%d")
            day = datetime_object2.strftime("%A")

            datetime_object3 = datetime.strptime(subject[3], "%H:%M")
            time = datetime_object3.strftime("%I:%M %p")
            phone = phone[0:3] + "-" + phone[3:6] + "-" + phone[6:]

            age = age
            gender = gender
            mode = mode
            notes = notes
            if mode == 'Online':
                location = 'Online - We will send you a Zoom link via email, 5 minutes before the appointment begins'
            else:
                location = '6055 Meridian Ave. Suite 40 A, San Jose, CA 95120.'
            # Send email to Client
            msg = Message(
                "Thanks for your Email!",
                sender="support@nityaayurveda.com",
                # recipients=[email],
                recipients=[email,
                            "pmarathay@gmail.com"],
            )
            # client email
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            msg.body = (
                "Hello " + str(name) + "," + "\n"
                "\n"
                "Thank you for making your appointment with us. \n"
                "Here are your appointment details: \n"
                "Date: " +
                str(day) + ", " + str(month_name) + " " +
                str(subject[2][8:10]) + ", " + str(subject[2][0:4]) + "\n"
                "Time: " + str(time) + "\n"
                "Location: " + str(location) + "\n"
                "\n"
                "If we need to contact you, we will use the following phone number and email: \n"
                "Name: " + str(name) + "\n"
                "Phone: " + str(phone) + "\n"
                "Email: " + str(email) + "\n"
                "\n"
                "Package purchased: " + str(subject[0]) + "\n"
                "Total amount paid: " + str(subject[1]) + "\n"
                "\n"
                "If you have any questions please call or text: \n"
                "Leena Marathay at 408-471-7004, \n"
                "Email Leena@nityaayurveda.com \n"
                "\n"
                "Thank you - Nitya Ayurveda\n\n"
            )
            mail.send(msg)

            # Send email to Practitioner
            msg2 = Message(
                "New appointment booked!",
                sender="support@nityaayurveda.com",
                # recipients=[email],
                recipients=["Lmarathay@yahoo.com",
                            "pmarathay@gmail.com"],
            )
            # practitioner email
            # msg = Message("Test email", sender='support@mealsfor.me', recipients=["pmarathay@gmail.com"])
            msg2.body = (
                "Hello Leena" + "\n"
                "\n"
                "Congratulations someone booked another appointment. \n"
                "Here are the appointment details: \n"
                "Date: " +
                str(day) + ", " + str(month_name) + " " +
                str(subject[2][8:10]) + ", " + str(subject[2][0:4]) + "\n"
                "Time: " + str(time) + "\n"
                "Location: " + str(location) + "\n"
                "\n"
                "Name: " + str(name) + "\n"
                "Phone: " + str(phone) + "\n"
                "Email: " + str(email) + "\n"
                "Age: " + str(age) + "\n"
                "Gender: " + str(gender) + "\n"
                "\n"
                "Package purchased: " + str(subject[0]) + "\n"
                "Total amount paid: " + str(subject[1]) + "\n"
                "Mode: " + str(mode) + "\n"
                "\n"
                "Notes: " + str(notes) + "\n"
            )
            mail.send(msg2)

            return "Email Sent", 200

        except:
            raise BadRequest("Request failed mail, please try again later.")
        finally:
            disconnect(conn)

    def post(self):

        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            msg = Message(
                "Thanks for your Email!",
                sender="support@nityaayurveda.com",
                recipients=[email, "Lmarathay@gmail.com",
                            "pmarathay@gmail.com"],
            )

            msg.body = (
                "Hi !\n\n"
                "We are looking forward to meeting with you! \n"
                "Email support@nityaayurveda.com if you need to get in touch with us directly.\n"
                "Thank you - Nitya Ayurveda\n\n"
            )
            # print('msg-bd----', msg.body)
            # print('msg-')
            mail.send(msg)
            return "Email Sent", 200

        except:
            raise BadRequest("Request failed mail, please try again later.")
        finally:
            disconnect(conn)


# ACCOUNT QUERIES
class findCustomerUIDv1(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            first_name = data["first_name"]
            last_name = data["last_name"]
            role = data["role"]
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
                    WHERE customer_phone_num = \'"""
                + phone
                + """\'
                        OR customer_email = \'"""
                + email
                + """\';
                """
            )
            items = execute(query, "get", conn)
            # print(items)
            thresholdEmail = []
            if len(items['result']) > 0:
                for cust in items['result']:
                    print('BEFORE PHONE CHECK', phone, cust['customer_phone_num'], fuzz.partial_ratio(
                        phone, cust['customer_phone_num']))
                    if phone == cust['customer_phone_num']:
                        print('AFTER PHONE CHECK', phone, cust['customer_phone_num'], fuzz.partial_ratio(
                            phone, cust['customer_phone_num']))

                        print('BEFORE EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                            email, cust['customer_email']))
                        if fuzz.partial_ratio(email, cust['customer_email']) > 90:
                            print('AFTER EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                                email, cust['customer_email']))
                            thresholdEmail.append(cust)

                        # else:
                        #     query = ["CALL nitya.new_customer_uid;"]
                        #     NewIDresponse = execute(query[0], "get", conn)
                        #     NewcustomerID = NewIDresponse["result"][0]["new_id"]
                        #     print('first name', first_name.split(' '))
                        #     if len(first_name.split(' ')) > 1:
                        #         fName = first_name.split(' ')[0]
                        #         lName = first_name.split(' ')[1]
                        #     customer_insert_query = (
                        #         """
                        #             INSERT INTO nitya.customers
                        #             SET customer_uid = \'"""
                        #         + NewcustomerID
                        #         + """\',
                        #                 customer_created_at = \'"""
                        #         + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                        #         + """\',
                        #                 customer_first_name = \'"""
                        #         + fName
                        #         + """\',
                        #                 customer_last_name = \'"""
                        #         + lName
                        #         + """\',
                        #                 customer_phone_num = \'"""
                        #         + phone
                        #         + """\',
                        #                 customer_email = \'"""
                        #         + email
                        #         + """\',
                        #                 role = \'"""
                        #         + role
                        #         + """\'
                        #             """
                        #     )

                        #     customer_items = execute(
                        #         customer_insert_query, "post", conn)
                        #     print("NewcustomerID=", NewcustomerID)
                        #     # items["message"] = "Email and Phone Number do not exist"
                        #     # items["code"] = 404
                        #     items["result"] = [{
                        #         "customer_uid": NewcustomerID,
                        #         "customer_phone_num": phone,
                        #         "customer_email": email
                        #     }]
                        #     items["message"] = "New Customer Created"
                        #     items["code"] = 200
                        #     return items
                    else:
                        print('AFTER ELSE PHONE CHECK', phone, cust['customer_phone_num'], fuzz.partial_ratio(
                            phone, cust['customer_phone_num']))

                        print('BEFORE ELSE EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                            email, cust['customer_email']))
                        if fuzz.partial_ratio(email, cust['customer_email']) > 90:
                            print('AFTER ELSE EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                                email, cust['customer_email']))

                            thresholdEmail.append(cust)
                        # else:
                        #     query = ["CALL nitya.new_customer_uid;"]
                        #     NewIDresponse = execute(query[0], "get", conn)
                        #     NewcustomerID = NewIDresponse["result"][0]["new_id"]
                        #     print('first name', first_name.split(' '))
                        #     if len(first_name.split(' ')) > 1:
                        #         fName = first_name.split(' ')[0]
                        #         lName = first_name.split(' ')[1]
                        #     customer_insert_query = (
                        #         """
                        #             INSERT INTO nitya.customers
                        #             SET customer_uid = \'"""
                        #         + NewcustomerID
                        #         + """\',
                        #                 customer_created_at = \'"""
                        #         + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                        #         + """\',
                        #                 customer_first_name = \'"""
                        #         + fName
                        #         + """\',
                        #                 customer_last_name = \'"""
                        #         + lName
                        #         + """\',
                        #                 customer_phone_num = \'"""
                        #         + phone
                        #         + """\',
                        #                 customer_email = \'"""
                        #         + email
                        #         + """\',
                        #                 role = \'"""
                        #         + role
                        #         + """\'
                        #             """
                        #     )

                        #     customer_items = execute(
                        #         customer_insert_query, "post", conn)
                        #     print("NewcustomerID=", NewcustomerID)
                        #     # items["message"] = "Email and Phone Number do not exist"
                        #     # items["code"] = 404
                        #     items["result"] = [{
                        #         "customer_uid": NewcustomerID,
                        #         "customer_phone_num": phone,
                        #         "customer_email": email
                        #     }]
                        #     items["message"] = "New Customer Created"
                        #     items["code"] = 200
                        #     return items

            else:
                query = ["CALL nitya.new_customer_uid;"]
                NewIDresponse = execute(query[0], "get", conn)
                NewcustomerID = NewIDresponse["result"][0]["new_id"]
                print('first name', first_name.split(' '))
                if len(first_name.split(' ')) > 1:
                    fName = first_name.split(' ')[0]
                    lName = first_name.split(' ')[1]
                else:
                    fName = first_name
                    lName = ''
                customer_insert_query = (
                    """
                        INSERT INTO nitya.customers
                        SET customer_uid = \'"""
                    + NewcustomerID
                    + """\',
                            customer_created_at = \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                            customer_first_name = \'"""
                    + fName
                    + """\',
                            customer_last_name = \'"""
                    + lName
                    + """\',
                            customer_phone_num = \'"""
                    + phone
                    + """\',
                            customer_email = \'"""
                    + email
                    + """\',
                            role = \'"""
                    + role
                    + """\'
                        """
                )

                customer_items = execute(customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)
                # items["message"] = "Email and Phone Number do not exist"
                # items["code"] = 404
                items["result"] = {
                    "customer_uid": NewcustomerID,
                    "customer_phone_num": phone,
                    "customer_email": email
                }
                items["message"] = "New Customer Created"
                items["code"] = 200
                return items
            print(thresholdEmail)
            if len(thresholdEmail) > 1:
                print('in if')
                for threshold in thresholdEmail:
                    for thresh in thresholdEmail:
                        if fuzz.partial_ratio(email, thresh['customer_email']) > fuzz.partial_ratio(email, threshold['customer_email']):
                            items["message"] = "Customer Found"
                            items["code"] = 200
                            items['result'] = thresh

            elif len(thresholdEmail) == 1:
                print('in elif')
                items["message"] = "Customer Found"
                items["code"] = 200
                items['result'] = thresholdEmail[0]
            else:
                print('else create new customer')
                query = ["CALL nitya.new_customer_uid;"]
                NewIDresponse = execute(query[0], "get", conn)
                NewcustomerID = NewIDresponse["result"][0]["new_id"]
                print('first name', first_name.split(' '))
                if len(first_name.split(' ')) > 1:
                    fName = first_name.split(' ')[0]
                    lName = first_name.split(' ')[1]
                else:
                    fName = first_name
                    lName = ''
                customer_insert_query = (
                    """
                        INSERT INTO nitya.customers
                        SET customer_uid = \'"""
                    + NewcustomerID
                    + """\',
                            customer_created_at = \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                            customer_first_name = \'"""
                    + fName
                    + """\',
                            customer_last_name = \'"""
                    + lName
                    + """\',
                            customer_phone_num = \'"""
                    + phone
                    + """\',
                            customer_email = \'"""
                    + email
                    + """\',
                            role = \'"""
                    + role
                    + """\'
                        """
                )

                customer_items = execute(
                    customer_insert_query, "post", conn)
                print("NewcustomerID=", NewcustomerID)
                # items["message"] = "Email and Phone Number do not exist"
                # items["code"] = 404
                items["result"] = {
                    "customer_uid": NewcustomerID,
                    "customer_phone_num": phone,
                    "customer_email": email
                }
                items["message"] = "New Customer Created"
                items["code"] = 200
                return items

            # items["message"] = "Customer Found"
            # items["code"] = 200
            return items
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)

class findCustomerUIDv2(Resource):
    def post(self):
        response = {}
        try:
            data = request.get_json()
            first_name = data["first_name"]
            last_name = data["last_name"]
            role = data["role"]
            phone = data["phone_num"]
            email = data["email"]
            is_ret_client_appt = data["is_ret_client_appt"]
            query = (
                """
                WITH matches AS (
                    SELECT customer_uid,
                        LCASE(customer_email) = LCASE(\'"""
                + email
                + """\') AS email_match,
                        customer_phone_num = \'"""
                + phone
                + """\' AS phone_match,
                        EXISTS(
                            SELECT 1
                            FROM nitya.appointments
                            WHERE appt_treatment_uid = '330-000010' 
                            AND appt_customer_uid = customer_uid
                        ) AS is_cust_eligible
                    FROM nitya.customers
                    WHERE customer_phone_num = \'"""
                + phone
                + """\' OR customer_email = \'"""
                + email
                + """\' ORDER BY 2 DESC, 3 DESC)
                SELECT customer_uid,
                    email_match,
                    phone_match,
                    CASE
                        WHEN email_match AND phone_match 
                        THEN is_cust_eligible
                        ELSE MAX(is_cust_eligible)
                    END AS is_eligible
                FROM matches;
                """
            )
            conn = connect()
            matched_user = execute(query, "get", conn)["result"][0]
            if matched_user["customer_uid"]:
                response["message"] = "Customer Found"
                response["code"] = 200
                response["customer_uid"] = matched_user.pop("customer_uid")
                response["email_match"] = matched_user["email_match"]
                response["phone_match"] = matched_user["phone_match"]
                if is_ret_client_appt:
                    is_intro_consult_done = matched_user.pop("is_eligible")
                    fields_matched = [v for v in matched_user.values()]
                    if not all(fields_matched) or \
                            (all(fields_matched) and not is_intro_consult_done):
                        response["warning"] = (
                            "Please Note that if you have not had an Initial "
                            "Consultation there may be additional charges.")
            else:
                if is_ret_client_appt:
                    raise BadRequest("This appointment is reserved for returning clients. "
                        "Please book an Initial Consultation or use the email "
                        "and phone number you used to book your Initial Consultation.")
                query = ("CALL nitya.new_customer_uid;")
                new_uid_response = execute(query, "get", conn)
                new_customer_uid = new_uid_response["result"][0]["new_id"]
                customer_insert_query = (
                    """
                        INSERT INTO nitya.customers
                        SET customer_uid = \'"""
                    + new_customer_uid
                    + """\',
                            customer_created_at = \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                            customer_first_name = \'"""
                    + first_name
                    + """\',
                            customer_last_name = \'"""
                    + last_name
                    + """\',
                            customer_phone_num = \'"""
                    + phone
                    + """\',
                            customer_email = \'"""
                    + email
                    + """\',
                            role = \'"""
                    + role
                    + """\'
                    """
                )
                execute(customer_insert_query, "post", conn)
                response["customer_uid"] = new_customer_uid
                response["message"] = "Customer created"
                response["code"] = 201
        except BadRequest as e:
            raise e
        except Exception as e:
            raise InternalServerError("An unknown error occurred") from e
        finally:
            disconnect(conn)
        return response

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
                data["social_id"] if data.get(
                    "social_id") is not None else "NULL"
            )
            city = data["city"]
            state = data["state"]
            zip_code = data["zip_code"]
            latitude = data["latitude"]
            longitude = data["longitude"]
            referral = data["referral_source"]
            role = data["role"]
            cust_id = data["cust_id"] if data.get(
                "cust_id") is not None else "NULL"

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

                password = sha512(
                    (data["password"] + salt).encode()).hexdigest()
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
                        WHERE customer_uid = \'"""
                    + cust_id
                    + """\';
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
                        customer_created_at = \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                        customer_first_name = \'"""
                    + firstName
                    + """\',
                        customer_last_name = \'"""
                    + lastName
                    + """\',
                        customer_phone_num = \'"""
                    + phone
                    + """\',
                        customer_address = \'"""
                    + address
                    + """\',
                        customer_unit = \'"""
                    + unit
                    + """\',
                        customer_city = \'"""
                    + city
                    + """\',
                        customer_state = \'"""
                    + state
                    + """\',
                        customer_zip = \'"""
                    + zip_code
                    + """\',
                        customer_lat = \'"""
                    + latitude
                    + """\',
                        customer_long = \'"""
                    + longitude
                    + """\',
                        password_salt = \'"""
                    + salt
                    + """\',
                        password_hashed = \'"""
                    + password
                    + """\',
                        password_algorithm = \'"""
                    + algorithm
                    + """\',
                        referral_source = \'"""
                    + referral
                    + """\',
                        role = \'"""
                    + role
                    + """\',
                        user_social_media = \'"""
                    + user_social_signup
                    + """\',
                        social_timestamp  =  DATE_ADD(now() , INTERVAL 14 DAY)
                        WHERE customer_uid = \'"""
                    + cust_id
                    + """\';
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

                            \'"""
                    + NewUserID
                    + """\',
                            \'"""
                    + (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                    + """\',
                            \'"""
                    + firstName
                    + """\',
                            \'"""
                    + lastName
                    + """\',
                            \'"""
                    + phone
                    + """\',
                            \'"""
                    + email
                    + """\',
                            \'"""
                    + address
                    + """\',
                            \'"""
                    + unit
                    + """\',
                            \'"""
                    + city
                    + """\',
                            \'"""
                    + state
                    + """\',
                            \'"""
                    + zip_code
                    + """\',
                            \'"""
                    + latitude
                    + """\',
                            \'"""
                    + longitude
                    + """\',
                            \'"""
                    + salt
                    + """\',
                            \'"""
                    + password
                    + """\',
                            \'"""
                    + algorithm
                    + """\',
                            \'"""
                    + referral
                    + """\',
                            \'"""
                    + role
                    + """\',
                            \'"""
                    + user_social_signup
                    + """\',
                            \'"""
                    + user_access_token
                    + """\',
                            DATE_ADD(now() , INTERVAL 14 DAY),
                            \'"""
                    + user_refresh_token
                    + """\',
                            \'"""
                    + mobile_access_token
                    + """\',
                            \'"""
                    + mobile_refresh_token
                    + """\',
                            \'"""
                    + social_id
                    + """\');"""
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
                    WHERE customer_email = \'"""
                + email
                + """\';
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


class UserSocialSignUp(Resource):
    def post(self):
        print("In UserSocialSignUp")
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)

            ts = getNow()

            customer_email = data['customer_email']
            customer_first_name = data['customer_first_name']
            customer_last_name = data['customer_last_name']
            customer_phone_num = data['customer_phone_num']
            role = data["role"]
            user_social_media = data["user_social_media"]
            user_access_token = data["user_access_token"]
            print(user_access_token)
            social_id = data["social_id"]
            print(social_id)
            user_refresh_token = data["user_refresh_token"]
            print(user_refresh_token)
            access_expires_in = data["access_expires_in"]
            print(access_expires_in)

            cust_id_response = execute("""SELECT customer_uid, password_hashed FROM customers
                                            WHERE customer_email = \'""" + customer_email + """\';""", 'get', conn)

            if len(cust_id_response['result']) > 0:
                print('Customer exists')
                response['message'] = "Email ID already exists."

            else:
                print('in else')
                new_customer_id_response = execute(
                    "CALL new_customer_uid;", 'get', conn)
                new_customer_id = new_customer_id_response['result'][0]['new_id']

                execute("""INSERT INTO customers
                        SET customer_uid = \'""" + new_customer_id + """\',
                            customer_created_at = \'""" + ts + """\',
                            customer_email = \'""" + customer_email + """\',
                            customer_first_name = \'""" + customer_first_name + """\',
                            customer_last_name = \'""" + customer_last_name + """\',
                            user_access_token = \'""" + user_access_token + """\',
                            social_id = \'""" + social_id + """\',
                            role = \'""" + role + """\',
                            user_social_media = \'""" + user_social_media + """\',
                            user_refresh_token = \'""" + user_refresh_token + """\',
                            access_expires_in = \'""" + access_expires_in + """\',
                            customer_phone_num = \'""" + customer_phone_num + """\';""", 'post', conn)
                response['message'] = 'successful'
                response['result'] = new_customer_id

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class UserSocialLogin(Resource):
    def get(self, email_id):
        print("In UserSocialLogin")
        response = {}
        items = {}

        try:
            conn = connect()
            # data = request.get_json(force=True)
            # email_id = data['email_id']
            # password = data['password']
            temp = False
            emails = execute(
                """SELECT customer_uid, customer_email, user_access_token from customers;""", 'get', conn)
            for i in range(len(emails['result'])):
                email = emails['result'][i]['customer_email']
                if email == email_id:
                    temp = True
                    customer_uid = emails['result'][i]['customer_uid']
                    user_access_token = emails["result"][i]["user_access_token"]
            if temp == True:

                response['result'] = customer_uid, user_access_token
                response['message'] = 'Correct Email'

            if temp == False:
                response['result'] = False
                response['message'] = 'Email ID doesnt exist'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class UserTokenEmail(Resource):
    def get(self, customer_email):
        print("In UserTokenEmail")
        response = {}
        items = {}

        try:
            conn = connect()
            query = None

            query = (
                """SELECT customer_uid
                                , customer_email
                                , user_access_token
                                ,user_refresh_token
                        FROM
                        customers WHERE customer_email = \'"""
                + customer_email
                + """\';"""
            )

            items = execute(query, "get", conn)
            print(items)
            response["message"] = "successful"
            response["customer_uid"] = items["result"][0]["customer_uid"]
            response["customer_email"] = items["result"][0]["customer_email"]
            response["user_access_token"] = items["result"][0]["user_access_token"]
            response["user_refresh_token"] = items["result"][0][
                "user_refresh_token"
            ]

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GetUserEmailId(Resource):
    def get(self, customer_email):
        print("In GetUserEmailID")
        response = {}
        items = {}

        try:
            conn = connect()

            temp = False
            emails = execute(
                """SELECT customer_email from customers where customer_email = \'""" + customer_email + """\';""", 'get', conn)
            print(emails)
            if len(emails['result']) > 0:
                response['message'] = emails['result'][0]['customer_email']
            else:
                response['message'] = 'User ID doesnt exist'

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class Login(Resource):
    def post(self):
        response = {}
        print('in login')
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
                    WHERE customer_email = \'"""
                + email
                + """\';
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
                    "SELECT * from nitya.customers WHERE customer_email = '"
                    + email
                    + "';"
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
        if desc == "NITYATEST":
            return {"publicKey": stripe_public_test_key}
        else:
            return {"publicKey": stripe_public_live_key}


# -- SEMINAR ---------------------------------


class SeminarRegister(Resource):
    def post(self):
        response = {}
        items = {}
        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            print("Received:", data)

            first_name = data["first_name"]
            # print(first_name)
            last_name = data["last_name"]
            # print(last_name)
            email = data["email"]
            # print(email)
            city = data["city"]
            # print(city)
            state = data["state"]
            # print(state)

            mode = data["mode"]
            # print(mode)
            notes = data["notes"]
            # print(mode)
            donation = data["donation"]
            # print(mode)
            if(len(donation) == 0):
                donation = str(0)
            else:
                donation = donation
            num_attendees = data["num_attendees"]

            print("Data Received")

            query = ["CALL nitya.new_seminar_uid;"]
            print(query)
            NewIDresponse = execute(query[0], "get", conn)
            print(NewIDresponse)
            NewID = NewIDresponse["result"][0]["new_id"]
            print("NewID = ", NewID)
            print(donation)
            query = (
                """
                    INSERT INTO nitya.seminar
                    SET seminar_uid  = \'"""
                + NewID
                + """\',
                        first_name = \'"""
                + first_name
                + """\',
                        last_name = \'"""
                + last_name
                + """\',
                        email = \'"""
                + email
                + """\',
                        city = \'"""
                + city
                + """\',
                        state = \'"""
                + state
                + """\',
                        mode = \'"""
                + mode + """\',
                        notes = \'"""
                + notes + """\',
                        donation = \'"""
                + donation + """\',
                        num_attendees = \'"""
                + num_attendees + """\';
                    """
            )

            items = execute(query, "post", conn)
            print(items)

            if items["code"] == 281:
                response["message"] = "Registration successful"
                return response, 200
            else:
                return items

        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class UpdateRegister(Resource):
    def post(self, seminar_id):
        print("\nInside update")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block")
            print("Received:", seminar_id)
            data = request.get_json(force=True)
            donation = data["donation"]

            query = (
                """
                    UPDATE nitya.seminar
                    SET donation = \'"""
                + donation + """\'
                    WHERE seminar_uid = \'"""
                + seminar_id
                + """\';
                    """
            )

            products = execute(query, "post", conn)
            print("Back in class")
            print(products)
            return products["code"]

        except:
            raise BadRequest("Delete Request failed, please try again later.")
        finally:
            disconnect(conn)


class findSeminarUID(Resource):
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
                    # QUERY 5

                    SELECT seminar_uid,
                        email
                    FROM nitya.seminar
                    WHERE email = \'"""
                + email
                + """\';
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


class WorkshopAttendees(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """
                SELECT
                    CONCAT(first_name, ' ', last_name) as name,
                    email,
                    CONCAT(city, ',',state) as city,
                    mode,
                    num_attenedees
                FROM nitya.seminar;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)


class RegistrationConfirmation(Resource):
    def post(self, email):
        try:
            conn = connect()
            data = request.get_json(force=True)
            name = data["name"]
            msg = Message(
                subject="Nitya Ayurveda Workshop Registration",
                sender="support@nityaayurveda.com",
                # recipients=[email]
                recipients=[email, "Lmarathay@gmail.com",
                            "pmarathay@gmail.com"],
            )

            msg.body = (
                "Hello " + str(name) + "\n"
                "\n"
                "Thank you for registering for the workshop “Eating Right For Your Body Type” on Saturday, January 29th at 2 P.M. Mountain Standard Time. Looking forward to seeing you soon.\n"
                "\n"
                "Regards," + "\n"
                "Leena Marathay" + "\n"
                "\n"
                "Here is the Zoom Meeting Detail:" + "\n"
                "\n"
                "Leena Marathay is inviting you to a scheduled Zoom meeting." + "\n"
                "\n"
                "Topic: Eating Right For Your Body Type" + "\n"
                "Time: Jan 29, 2022 02: 00 PM Mountain Time(US and Canada)" + "\n"
                "\n"
                'Join Zoom Meeting' + "\n"
                "https: // us02web.zoom.us/j/85853482826?pwd=cWhHZllNOXJKemdlWXpadG1YZFYwQT09" + "\n"
                "\n"
                "Meeting ID: 858 5348 2826" + "\n"
                "Passcode: T3zTn3" + "\n"
                "One tap mobile" + "\n"
                " + 13462487799, , 85853482826  # ,,,,*062162# US (Houston)" +
                "\n"
                " + 16699006833, , 85853482826  # ,,,,*062162# US (San Jose)" + "\n"
                "\n"
                "Dial by your location" + "\n"
                " + 1 346 248 7799 US(Houston)" + "\n"
                " + 1 669 900 6833 US(San Jose)" + "\n"
                ' + 1 253 215 8782 US(Tacoma)' + "\n"
                " + 1 312 626 6799 US(Chicago)" + "\n"
                " + 1 929 205 6099 US(New York)" + "\n"
                " + 1 301 715 8592 US(Washington DC)" + "\n"
                "Meeting ID: 858 5348 2826"+"\n"
                "Passcode: 062162"+"\n"
                "Find your local number: https: // us02web.zoom.us/u/kbyiau6FLS"+"\n"

            )

            print(msg.body)
            mail.send(msg)
            return "Email Sent"
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


# -- Nitya Database Queries start here -------------------------------------------------------------------------------

class Diseases (Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """
                SELECT * FROM nitya.diseases;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)

class Symptoms (Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """
                SELECT * FROM nitya.symptoms;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Symptoms GET Request failed, please try again later.")
        finally:
            disconnect(conn)

    def post(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            data = request.get_json(force=True)
            print("Received:", data)
            symptom_uid = "(" + str(data["symptom_uid"])[1:-1] + ")"
            print("Symptom_UID:", symptom_uid)
            # symptom_uid =str(('550-000001', '550-000002'))
            
            
            # QUERY 1 (WHERE a.ds_symptom_uid in """ + symptom_uid + """)
            query = """
                SELECT *
                FROM nitya.symptoms
                WHERE symptoms.symptom_uid in """ + symptom_uid + """
                """
            print(query)
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # print("Query Result: ", items["result"])
            

            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Symptoms POST Request failed, please try again later.")
        finally:
            disconnect(conn)

class Diseases_Symptoms (Resource):
    def get(self):
        response = {}
        items = {}
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """
                SELECT * 
                FROM nitya.ds
                LEFT JOIN nitya.diseases
                ON ds.ds_disease_uid = diseases.disease_uid
                LEFT JOIN nitya.symptoms
                ON ds.ds_symptom_uid = symptoms.symptom_uid;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)



class DiseasesFromSymptoms (Resource):
    def get(self, symptom_uid):
        response = {}
        items = {}
        print("\nInside DiseasesFromSymptoms", symptom_uid)
        try:
            # Connect to the DataBase
            conn = connect()
            # QUERY 1
            query = """
                SELECT * 
                FROM nitya.ds
                LEFT JOIN nitya.diseases
                ON ds.ds_disease_uid = diseases.disease_uid
                LEFT JOIN nitya.symptoms
                ON ds.ds_symptom_uid = symptoms.symptom_uid
                WHERE symptom_uid = \'""" + symptom_uid + """\';
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "Appointments Request failed, please try again later.")
        finally:
            disconnect(conn)

class DSFromSymptoms (Resource):
    def post(self):
        response = {}
        items = {}
        print("\nInside DSFromSymptoms")
        try:
            # Connect to the DataBase
            conn = connect()
            data = request.get_json(force=True)
            print("Received:", data)
            symptom_uid = "(" + str(data["symptom_uid"])[1:-1] + ")"
            print("Symptom_UID:", symptom_uid)
            # symptom_uid =str(('550-000001', '550-000002'))
            
            
            # QUERY 1 (WHERE a.ds_symptom_uid in """ + symptom_uid + """)
            setSessionQuery = """ SET SESSION group_concat_max_len = @@max_allowed_packet;"""
            setSession = execute(setSessionQuery, "get", conn)
            response["set session"] = setSession["result"]

            query = """
               
                SELECT d_uid AS disease_uid, disease_name, disease_description,CONCAT('[',GROUP_CONCAT(JSON_OBJECT('s_uid', symptom_uid,'s_name', symptom_name)),']') AS sym_uid_name
                FROM (
                -- Diseases associated with the input Symptoms
                    SELECT DISTINCT
                        ds_disease_uid AS d_uid,
                        diseases.disease_name,
                        diseases.disease_description
                    FROM nitya.ds a
                    LEFT JOIN nitya.diseases
                        ON a.ds_disease_uid = diseases.disease_uid
                    WHERE a.ds_symptom_uid in """ + symptom_uid + """
                    )AS d
                LEFT JOIN (
                -- Symptoms names and description
                    SELECT *
                    FROM nitya.ds
                    LEFT JOIN (
                        SELECT *
                        FROM nitya.symptoms
                        ) AS s
                    ON ds_symptom_uid = s.symptom_uid
                    ) AS b
                ON d.d_uid = b.ds_disease_uid
                GROUP BY d_uid;
                """
            # print(query)
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # print("Query Result: ", items["result"])
            

            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "DSFromSymptoms Endpoint Failed.")
        finally:
            disconnect(conn)

# NEW ENDPOINT IS FOR TESTING AND DEVELOPMENT ONLY
class NewEndpoint (Resource):
    def post(self):
        response = {}
        items = {}
        print("\nInside NewEndpoint")
        try:
            # Connect to the DataBase
            conn = connect()
            data = request.get_json(force=True)
            print("Received:", data)
            symptom_uid = "(" + str(data["symptom_uid"])[1:-1] + ")"
            print("Symptom_UID:", symptom_uid)
            # symptom_uid =str(('550-000001', '550-000002'))
            
            
            # QUERY 1 (WHERE a.ds_symptom_uid in """ + symptom_uid + """)
            query = """
                SELECT *
                FROM nitya.symptoms
                WHERE symptoms.symptom_uid in """ + symptom_uid + """
                """
            print(query)
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful"
            response["result"] = items["result"]
            # print("Query Result: ", items["result"])
            

            # Returns code and response
            return response, 200
        except:
            raise BadRequest(
                "New Endpoint Failed.")
        finally:
            disconnect(conn)
# -- DEFINE APIS -------------------------------------------------------------------------------


# Define API routes

api.add_resource(appointments, "/api/v2/appointments")
api.add_resource(treatments, "/api/v2/treatments")

api.add_resource(availability, "/api/v2/availability")
api.add_resource(updateAvailability, "/api/v2/updateAvailability")

api.add_resource(unavailability, "/api/v2/unavailability")
api.add_resource(updateUnavailability, "/api/v2/updateUnavailability")
api.add_resource(deleteUnavailability,
                 "/api/v2/deleteUnavailability/<string:id>")

api.add_resource(FullBlog, "/api/v2/fullBlog/<string:blog_id>")
api.add_resource(TruncatedBlog, "/api/v2/truncatedBlog")
api.add_resource(AddBlog, "/api/v2/addBlog")
api.add_resource(UploadImage, "/api/v2/uploadImage")

api.add_resource(UploadVideo, "/api/v2/uploadVideo")
api.add_resource(DeleteBlog, "/api/v2/deleteBlog/<string:blog_id>")

api.add_resource(
    GetUserEmailId, '/api/v2/GetUserEmailId/<string:customer_email>')
api.add_resource(
    UserTokenEmail, '/api/v2/UserTokenEmail/<string:customer_email>')

api.add_resource(
    OneCustomerAppointments, "/api/v2/oneCustomerAppointments/<string:customer_uid>"
)
api.add_resource(CreateAppointment, "/api/v2/createAppointment")
api.add_resource(AddTreatment, "/api/v2/addTreatment")
api.add_resource(UpdateTreatment, "/api/v2/updateTreatment")

api.add_resource(
    GoogleCalenderEvents,
    "/api/v2/calenderEvents/<string:customer_uid>,<string:start>,<string:end>",
)
api.add_resource(UpdateAccessToken,
                 "/api/v2/UpdateAccessToken/<string:customer_uid>")
api.add_resource(CustomerToken, "/api/v2/customerToken/<string:customer_uid>")
api.add_resource(
    AvailableAppointments,
    "/api/v2/availableAppointments/<string:date_value>/<string:duration>/<string:mode>",
)
api.add_resource(AddContact, "/api/v2/addContact")
api.add_resource(purchaseDetails, "/api/v2/purchases")

api.add_resource(SendEmail, "/api/v2/sendEmail")
api.add_resource(SendEmailPaymentIntent, "/api/v2/SendEmailPaymentIntent")
api.add_resource(SendEmailCRON_CLASS, "/api/v2/sendEmailCRON_CLASS")
api.add_resource(findCustomerUIDv1, "/api/v1/findCustomer")
api.add_resource(findCustomerUIDv2, "/api/v2/findCustomer")
api.add_resource(createAccount, "/api/v2/createAccount")
api.add_resource(AccountSalt, "/api/v2/AccountSalt")
api.add_resource(Login, "/api/v2/Login")
api.add_resource(stripe_key, "/api/v2/stripe_key/<string:desc>")
api.add_resource(UserSocialLogin, '/api/v2/UserSocialLogin/<string:email_id>')

api.add_resource(UserSocialSignUp, '/api/v2/UserSocialSignUp')
api.add_resource(SeminarRegister, "/api/v2/SeminarRegister")
api.add_resource(UpdateRegister, "/api/v2/UpdateRegister/<string:seminar_id>")
api.add_resource(findSeminarUID, "/api/v2/findSeminarUID")

api.add_resource(WorkshopAttendees, "/api/v2/WorkshopAttendees")
api.add_resource(
    RegistrationConfirmation, "/api/v2/RegistrationConfirmation/<string:email>"
)


api.add_resource(Diseases, "/api/v2/diseases")
api.add_resource(Symptoms, "/api/v2/symptoms")
api.add_resource(Diseases_Symptoms, "/api/v2/ds")

api.add_resource(DSFromSymptoms, "/api/v2/dsfroms")
api.add_resource(DiseasesFromSymptoms, "/api/v2/dfroms/<string:symptom_uid>")

api.add_resource(NewEndpoint, "/api/v2/newEndpoint")
# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4000)
