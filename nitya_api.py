# To run program:  python3 nitya_api.py

# README:  if conn error make sure password is set properly in RDS PASSWORD section
# README:  Debug Mode may need to be set to False when deploying live (although it seems to be working through Zappa)
# README:  if there are errors, make sure you have all requirements are loaded



import os
import boto3
import json
import sys
import json
import pytz
import pymysql
import requests
import stripe
# from fuzzywuzzy import fuzz

from dotenv import load_dotenv
from datetime import date, datetime
from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.exceptions import BadRequest, InternalServerError
from decimal import Decimal
from datetime import datetime, date
from hashlib import sha512

# print("In Nitya")
print(f"-------------------- New Program Run ( {os.getenv('RDS_DB')} ) --------------------")

#  NEED TO SOLVE THIS
# from NotificationHub import Notification
# from NotificationHub import NotificationHub

# BING API KEY
# Import Bing API key into bing_api_key.py

#  NEED TO SOLVE THIS
# from env_keys import BING_API_KEY, RDS_PW


# app = Flask(__name__)
app = Flask(__name__)
api = Api(app)
# load_dotenv()

CORS(app)
# CORS(app, resources={r'/api/*': {'origins': '*'}})

# Set this to false when deploying to live application
app.config['DEBUG'] = True

# --------------- Google Scopes and Credentials------------------
SCOPES = "https://www.googleapis.com/auth/calendar"
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "nitya-ayurveda"



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


# app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY")

# use below for local testing
# stripe.api_key = stripe_secret_test_key
# stripe.api_key = ""sk_test_51J0UzOLGBFAvIBPFAm7Y5XGQ5APR...WTenXV4Q9ANpztS7Y7ghtwb007quqRPZ3""



# --------------- Mail Variables ------------------
# Mail username and password loaded in .env file
app.config['MAIL_USERNAME'] = os.getenv('SUPPORT_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('SUPPORT_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
# print("Sender: ", app.config['MAIL_DEFAULT_SENDER'])


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

# MAIL  -- This statement has to be below the Mail Variables
mail = Mail(app)



# --------------- Time Variables ------------------
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



# --------------- S3 BUCKET CONFIGUATION ------------------
s3 = boto3.client("s3")

# aws s3 bucket where the image is stored
# BUCKET_NAME = os.environ.get('nitya-images')
# BUCKET_NAME = "nitya-images"
BUCKET_NAME =os.getenv('BUCKET_NAME')
# print("Bucket Name: ", BUCKET_NAME)
# allowed extensions for uploading a profile photo file
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])


# For Push notification
isDebug = False
NOTIFICATION_HUB_KEY = os.getenv("NOTIFICATION_HUB_KEY")
NOTIFICATION_HUB_NAME = os.getenv("NOTIFICATION_HUB_NAME")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")



# --------------- DATABASE CONFIGUATION ------------------
# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    # print("RDS_HOST: ", os.getenv('RDS_HOST'))
    # print("RDS_USER: ", os.getenv('RDS_USER'))
    # print("RDS_PORT: ", os.getenv('RDS_PORT'), type(os.getenv('RDS_PORT')))
    # print("RDS_PW: ", os.getenv('RDS_PW'))
    # print("RDS_DB: ", os.getenv('RDS_DB'))

   
    try:
        conn = pymysql.connect(
            host=os.getenv('RDS_HOST'),
            user=os.getenv('RDS_USER'),
            port=int(os.getenv('RDS_PORT')),
            passwd=os.getenv('RDS_PW'),
            db=os.getenv('RDS_DB'),
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
        # response["sql"] = sql
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
                WHERE availability = "Available" OR availability = "Not Available"
                ORDER BY category, display_order;
                """
            # The query is executed here
            items = execute(query, "get", conn)
            # The return message and result from query execution
            response["message"] = "successful ec2"
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
        
class UploadDocument(Resource):
    def post(self):
        print("In Upload Document")
        response = {}
        try:
            data = request.form
            print("Received:", data)
            #  GET CUSTOMER APPOINTMENT INFO
            first_name = data.get("first_name", "Dear")
            last_name = data.get("last_name", "Customer")
            email = data.get("email", "pmarathay@yahoo.com")
            phone_no = data.get("phone_no", "4084760001")
            print(first_name, last_name, email, phone_no)

            item_document = request.files.get("file-0")
            print("Item Document: ", item_document)
            bucket = "nitya-images"
            uid = request.form.get("filename")
            TimeStamp_test = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            # print("Datetime: ", TimeStamp_test)
            key = "waivers/" + str(uid) + "_" + TimeStamp_test
            print(key)

            filename = (
                "https://s3-us-west-1.amazonaws.com/" +
                str(bucket) + "/" + str(key)
            )
            print("Filename: ", filename)

            # Determine the content type based on the file extension
            content_type = item_document.content_type

            print("Bucket: ", bucket)
            print("Body: ", item_document)
            print("Key: ", key)
            print("ACL: ", "public-read")
            print("ContentType: ", content_type)

            upload_file = s3.put_object(
                Bucket=bucket,
                Body=item_document,
                Key=key,
                ACL="public-read",
                ContentType=content_type,
            )
            # print("Upload details: ", upload_file)
            # print(upload_file['ResponseMetadata'])
            # print(upload_file['ResponseMetadata']['HTTPStatusCode'])
            if upload_file['ResponseMetadata']['HTTPStatusCode'] == 200:
                # print("Upload Successful")
                response["filename"] = filename
                response["link"] = filename

                # print('os.environ.get("SUPPORT_EMAIL")', os.environ.get("SUPPORT_EMAIL"))
                # print('response', response)
                
                msg = Message(
                "Here is the waiver",
                sender="support@nityaayurveda.com",
                # recipients=[email],
                recipients=[email,
                            "lmarathay@gmail.com",
                            "pmarathay@gmail.com"],
                )

                name = first_name + " " + last_name

                msg.body = (
                    "Hello " + str(name) + "\n"
                    "\n"
                    "Here is the waiver form you filled out and submitted.  Click on the link below to see the form.\n"
                    "\n"
                    "Regards," + "\n"
                    "Leena Marathay" + "\n"
                    "\n" +
                    str(filename)
                )

                mail.send(msg)

                response["message"] = "email sent"



            else:
                response["error"] = "file not uploaded"


            return response
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
        print("In CreateAppointment POST")
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
            
            # VALIDATE APPOINTMENT DATE - ONLY ALLOW NEXT DAY OR LATER
            from datetime import datetime, timedelta
            try:
                appointment_datetime = datetime.strptime(f"{datevalue} {timevalue}", "%Y-%m-%d %H:%M")
                current_datetime = datetime.now()
                
                # Get tomorrow's date (next day at 00:00:00)
                tomorrow = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                
                print(f"Appointment datetime: {appointment_datetime}")
                print(f"Current datetime: {current_datetime}")
                print(f"Tomorrow (earliest allowed): {tomorrow}")
                
                if appointment_datetime < tomorrow:
                    # Check if it's same day or past date
                    appointment_date = appointment_datetime.date()
                    current_date = current_datetime.date()
                    
                    if appointment_date == current_date:
                        print("ERROR: Cannot book appointment for same day")
                        raise BadRequest("For same day appointments please contact the Practitioner directly.")
                    else:
                        print("ERROR: Cannot book appointment in the past")
                        raise BadRequest("Error: Appointment date is invalid. Please select a future date.")
                    
                print("Appointment date validation passed - booking for next day or later")
                
            except ValueError as e:
                print(f"ERROR: Invalid date/time format: {e}")
                raise BadRequest("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
            except Exception as e:
                print(f"ERROR: Date validation failed: {e}")
                raise BadRequest(f"Date validation failed: {str(e)}")

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
            print("Email sent")
            
            # Create Google Calendar event for practitioner
            try:
                print("=== CREATING GOOGLE CALENDAR EVENT ===")
                
                # Get treatment duration for calendar event
                treatment_query = f"""
                    SELECT duration FROM nitya.treatments 
                    WHERE treatment_uid = '{treatment_uid}'
                """
                treatment_duration = execute(treatment_query, "get", conn)
                duration = treatment_duration['result'][0]['duration'] if treatment_duration['result'] else "01:00"
                
                # Determine location based on mode
                if mode == 'Online':
                    location = 'Online - Zoom link will be sent via email'
                else:
                    location = '1610 Blossom Hill Rd. Suite 1, San Jose, CA 95124'
                
                # Prepare appointment details for calendar event
                appointment_details = {
                    'customer_name': name,
                    'customer_email': email,
                    'customer_phone': phone_no,
                    'treatment_title': treatment['result'][0]['title'],
                    'date': datevalue,
                    'time': timevalue,
                    'duration': duration,
                    'age': age,
                    'gender': gender,
                    'mode': mode,
                    'notes': str(notes),
                    'purchase_price': purchase_price,
                    'location': location
                }
                
                # Create calendar event for practitioner (user 100-000093)
                calendar_event = create_google_calendar_event("100-000093", appointment_details)
                
                if calendar_event:
                    print(f"Google Calendar event created successfully: {calendar_event.get('id')}")
                    response["calendar_event_id"] = calendar_event.get('id')
                    response["calendar_event_url"] = calendar_event.get('htmlLink')
                else:
                    print("Failed to create Google Calendar event")
                    response["calendar_error"] = "Appointment created but calendar event failed"
                    
            except Exception as e:
                print(f"Error creating Google Calendar event: {e}")
                response["calendar_error"] = f"Appointment created but calendar event failed: {str(e)}"
            
            return response, 200
        except BadRequest as e:
            # Re-raise BadRequest exceptions to preserve custom error messages
            raise e
        except Exception as e:
            print(f"Unexpected error in CreateAppointment: {e}")
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
            # print("Received:", data)

            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            addon_cost = data["addon_cost"]
            availability = data["availability"]
            duration = data["duration"]
            treatment_notes = data["treatment_notes"]
            display_order = data["display_order"]
            image_url = data["image_url"]

            # print("treatment_notes:", treatment_notes)
            # print("display_order:", display_order)
            

            query = ["CALL nitya.new_treatment_uid;"]
            NewIDresponse = execute(query[0], "get", conn)
            NewID = NewIDresponse["result"][0]["new_id"]
            # print("NewID = ", NewID)

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
                        addon_cost = \'"""
                + addon_cost
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

            response["message"] = "Add Treatment successful"
            response["result"] = NewID
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
            # print("Received:", data)

            id = data["treatment_uid"]
            title = data["title"]
            category = data["category"]
            description = data["description"]
            cost = data["cost"]
            addon_cost = data["addon_cost"]
            availability = data["availability"]
            duration = data["duration"]
            treatment_notes = data["treatment_notes"]
            display_order = data["display_order"]
            image_url = data["image_url"]

            # print("Update ID = ", id)

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
                        addon_cost = \'"""
                + addon_cost
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
            # print(items)

            if items["code"] == 281:
                response["message"] = "Update Treatment Successful"
                return response, 200
            else:
                return items
        except:
            raise BadRequest(
                "Treatments Request failed, please try again later.")
        finally:
            disconnect(conn)


class DeleteTreatment(Resource):
    def post(self):
        print("\nInside DELETE Treatment")
        response = {}
        items = {}

        try:
            conn = connect()
            data = request.get_json(force=True)
            # print to Received data to Terminal
            # print("Received:", data)

            id = data["treatment_uid"]

            query = (
                """
                    UPDATE nitya.treatments
                    SET availability = 'DELETED'
                    WHERE treatment_uid = \'"""
                + id
                + """\';
                    """
            )

            delTreatment = execute(query, "post", conn)
            # print("Back in class")
            # print(delTreatment)
            response["message"] = "Treatment Availability changed to Not Available"
            return (response, delTreatment["code"])

        except:
            raise BadRequest("Delete Request failed, please try again later.")
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
    def get(self, date_value, duration_str):
        print("\nInside Available Appointments")
        response = {}
        items = {}

        try:
            conn = connect()
            print("Inside try block", date_value, duration_str)
            
            # VALIDATE APPOINTMENT DATE - PREVENT BOOKING TODAY OR IN THE PAST
            from datetime import datetime
            try:
                appointment_date = datetime.strptime(date_value, '%Y-%m-%d').date()
                current_date = datetime.now().date()
                
                print(f"Appointment date: {appointment_date}")
                print(f"Current date: {current_date}")
                
                if appointment_date <= current_date:
                    print("ERROR: Cannot show availability for today or past dates")
                    return {
                        "message": "No available time slots found for the selected date.",
                        "code": 280,
                        "result": [],
                        "no_availability": True,
                        "sql": "Date validation - past/today not allowed"
                    }
                    
                print("Date validation passed - showing availability for future date")
                
            except ValueError as e:
                print(f"ERROR: Invalid date format: {e}")
                return {
                    "message": "No available time slots found for the selected date.",
                    "code": 280,
                    "result": [],
                    "no_availability": True,
                    "sql": f"Invalid date format: {str(e)}"
                }

            # Test simple query first
            test_query = "SELECT 1 as test"
            test_result = execute(test_query, "get", conn)
            print("Test query result:", test_result)

            # Calculate duration in seconds and slots needed
            duration_secs = 1 * 3600 + 59 * 60 + 59  # 1:59:59 in seconds
            slots_needed = (duration_secs + 1799) // 1800  # Ceiling division for 30-min slots
            
            # Main query with direct parameter substitution
            query = """
                -- ------------------------------
                -- FINAL VERSION with subquery: allows filtering only 'OK'
                -- ------------------------------
                -- Set your test inputs here:
                -- SET @date_value = '2025-09-14';       -- appointment date to test
                -- SET @duration_str = '1:29:59';        -- appointment duration to test (HH:MM:SS)

                SELECT *
                FROM (
                    SELECT 
                        ts.time_slot_uid,
                        DATE_FORMAT(CAST(ts.begin_datetime AS TIME), '%h:%i %p') AS available_time,
                        DATE_FORMAT(
                            DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND), '%h:%i %p'  -- Python placeholder
                            -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND), '%h:%i %p'  -- MySQL version
                        ) AS end_time,
                        d.hoursMode,
                        CASE 
                            WHEN CAST(ts.begin_datetime AS TIME) >= d.morning_start_time 
                            AND (
                                DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                            ) <= d.morning_end_time THEN 1 
                            ELSE 0 
                        END AS in_morning,
                        CASE 
                            WHEN CAST(ts.begin_datetime AS TIME) >= d.afternoon_start_time 
                            AND (
                                DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                            ) <= d.afternoon_end_time THEN 1 
                            ELSE 0 
                        END AS in_afternoon,
                        CASE 
                            WHEN (CAST(ts.begin_datetime AS TIME) >= d.morning_start_time 
                                AND (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                ) <= d.morning_end_time)
                            OR (CAST(ts.begin_datetime AS TIME) >= d.afternoon_start_time 
                                AND (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                ) <= d.afternoon_end_time) THEN 1 
                            ELSE 0 
                        END AS in_open_hours,
                        CASE 
                            WHEN EXISTS (
                                SELECT 1 FROM practioner_availability pa 
                                WHERE pa.date = '{}'  -- Python placeholder
                                -- WHERE pa.date = @date_value   -- MySQL version
                                AND TIME(STR_TO_DATE(pa.start_time_notavailable, '%H:%i:%s')) < (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                )
                                AND TIME(STR_TO_DATE(pa.end_time_notavailable, '%H:%i:%s')) > CAST(ts.begin_datetime AS TIME)
                            ) THEN 1 
                            ELSE 0 
                        END AS blocked_by_practitioner,
                        CASE 
                            WHEN EXISTS (
                                SELECT 1 FROM appointments a
                                LEFT JOIN treatments t ON a.appt_treatment_uid = t.treatment_uid
                                WHERE a.appt_date = '{}'  -- Python placeholder
                                -- WHERE a.appt_date = @date_value   -- MySQL version
                                AND TIME(ADDTIME(STR_TO_DATE(a.appt_time, '%H:%i:%s'), STR_TO_DATE(t.duration, '%H:%i:%s'))) > CAST(ts.begin_datetime AS TIME)
                                AND TIME(STR_TO_DATE(a.appt_time, '%H:%i:%s')) < (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                )
                            ) THEN 1 
                            ELSE 0 
                        END AS blocked_by_appointment,
                        CASE
                            WHEN ((CAST(ts.begin_datetime AS TIME) >= d.morning_start_time 
                                AND (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                ) <= d.morning_end_time)
                            OR (CAST(ts.begin_datetime AS TIME) >= d.afternoon_start_time 
                                AND (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                ) <= d.afternoon_end_time)) = 0 THEN 'OUTSIDE_HOURS'
                            WHEN EXISTS (
                                SELECT 1 FROM practioner_availability pa 
                                WHERE pa.date = '{}'  -- Python placeholder
                                -- WHERE pa.date = @date_value   -- MySQL version
                                AND TIME(STR_TO_DATE(pa.start_time_notavailable, '%H:%i:%s')) < (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                )
                                AND TIME(STR_TO_DATE(pa.end_time_notavailable, '%H:%i:%s')) > CAST(ts.begin_datetime AS TIME)
                            ) THEN 'BLOCKED_PRACTITIONER'
                            WHEN EXISTS (
                                SELECT 1 FROM appointments a
                                LEFT JOIN treatments t ON a.appt_treatment_uid = t.treatment_uid
                                WHERE a.appt_date = '{}'  -- Python placeholder
                                -- WHERE a.appt_date = @date_value   -- MySQL version
                                AND TIME(ADDTIME(STR_TO_DATE(a.appt_time, '%H:%i:%s'), STR_TO_DATE(t.duration, '%H:%i:%s'))) > CAST(ts.begin_datetime AS TIME)
                                AND TIME(STR_TO_DATE(a.appt_time, '%H:%i:%s')) < (
                                    DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                                    -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                                )
                            ) THEN 'BLOCKED_APPOINTMENT'
                            ELSE 'OK'
                        END AS availability_status
                    FROM time_slots ts
                    CROSS JOIN days d
                    WHERE d.dayofweek = DAYOFWEEK(STR_TO_DATE('{}', '%Y-%m-%d'))  -- Python placeholder
                    -- WHERE d.dayofweek = DAYOFWEEK(@date_value)  -- MySQL version
                    AND (
                        (CAST(ts.begin_datetime AS TIME) >= d.morning_start_time 
                        AND (
                            DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                            -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                        ) <= d.morning_end_time)
                        OR 
                        (CAST(ts.begin_datetime AS TIME) >= d.afternoon_start_time 
                        AND (
                            DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC('{}') SECOND)  -- Python placeholder
                            -- DATE_ADD(CAST(ts.begin_datetime AS TIME), INTERVAL TIME_TO_SEC(@duration_str) SECOND)  -- MySQL version
                        ) <= d.afternoon_end_time)
                    )
                    ORDER BY d.hoursMode, CAST(ts.begin_datetime AS TIME)
                ) q
                -- WHERE q.availability_status = 'OK'
                ORDER BY q.hoursMode, in_afternoon, q.available_time;
            """

            # print("Query: ", query)
            formatted_query = query.format(
                duration_str,  # 1st placeholder - duration for end_time
                duration_str,  # 2nd placeholder - duration for in_morning
                duration_str,  # 3rd placeholder - duration for in_afternoon
                duration_str,  # 4th placeholder - duration for in_open_hours
                duration_str,  # 5th placeholder - duration for in_open_hours
                date_value,    # 6th placeholder - date for blocked_by_practitioner
                duration_str,  # 7th placeholder - duration for blocked_by_practitioner
                date_value,    # 8th placeholder - date for blocked_by_appointment
                duration_str,  # 9th placeholder - duration for blocked_by_appointment
                duration_str,  # 10th placeholder - duration for availability_status OUTSIDE_HOURS
                duration_str,  # 11th placeholder - duration for availability_status OUTSIDE_HOURS
                date_value,    # 12th placeholder - date for availability_status BLOCKED_PRACTITIONER
                duration_str,  # 13th placeholder - duration for availability_status BLOCKED_PRACTITIONER
                date_value,    # 14th placeholder - date for availability_status BLOCKED_APPOINTMENT
                duration_str,  # 15th placeholder - duration for availability_status BLOCKED_APPOINTMENT
                date_value,    # 16th placeholder - date for WHERE clause
                duration_str,  # 17th placeholder - duration for WHERE clause morning
                duration_str   # 18th placeholder - duration for WHERE clause afternoon
            )
            print("Formatted Query: ", formatted_query)
            available_times = execute(formatted_query, "get", conn)
            print("Execute response: ", available_times)
            if "result" in available_times:
                print("Available Times: ", str(available_times["result"]))
                print("Number of time slots: ", len(available_times["result"]))
                
                # Check if no times are available
                if len(available_times["result"]) == 0:
                    print("No available time slots found for the selected date")
                    available_times["message"] = "No available time slots found for the selected date. Please try a different date or contact the practitioner directly."
                    available_times["no_availability"] = True
                    return available_times
                
                # Get Google Calendar FreeBusy data for user 100-000093
                print("=== GOOGLE CALENDAR INTEGRATION ===")
                print("Checking Google Calendar for user 100-000093...")
                
                # Check only the specific appointment date (more efficient)
                from datetime import datetime
                appointment_date = datetime.strptime(date_value, '%Y-%m-%d')
                
                # Set date range for FreeBusy check - only the appointment date
                freebusy_start = appointment_date.strftime('%Y-%m-%dT00:00:00Z')
                freebusy_end = appointment_date.strftime('%Y-%m-%dT23:59:59Z')
                
                print(f"FreeBusy check for specific date:")
                print(f"  Appointment date: {appointment_date.strftime('%Y-%m-%d')}")
                print(f"  FreeBusy range: {freebusy_start} to {freebusy_end}")
                
                # Get FreeBusy data for the specific date only
                freebusy_data = get_freebusy_data("100-000093", freebusy_start, freebusy_end)
                
                if freebusy_data:
                    print("FreeBusy data retrieved successfully")
                    print(f"FreeBusy data: {freebusy_data}")
                    
                    # Since we're only checking the specific date, we can use the busy periods directly
                    appointment_busy_periods = []
                    for calendar_id, calendar_data in freebusy_data.get('calendars', {}).items():
                        if 'busy' in calendar_data:
                            for busy_period in calendar_data['busy']:
                                if 'start' in busy_period and 'end' in busy_period:
                                    from datetime import datetime
                                    import pytz
                                    
                                    pacific = pytz.timezone('US/Pacific')
                                    busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                                    busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                                    
                                    busy_start_pacific = busy_start.astimezone(pacific)
                                    busy_end_pacific = busy_end.astimezone(pacific)
                                    
                                    appointment_busy_periods.append({
                                        'start': busy_start_pacific,
                                        'end': busy_end_pacific
                                    })
                    
                    print(f"Found {len(appointment_busy_periods)} busy periods for {date_value}")
                    
                    # Update availability_status based on Google Calendar
                    blocked_count = 0
                    for time_slot in available_times["result"]:
                        if "available_time" in time_slot and "end_time" in time_slot:
                            is_busy = is_time_slot_busy_optimized(
                                time_slot["available_time"], 
                                time_slot["end_time"], 
                                appointment_busy_periods,
                                date_value
                            )
                            
                            if is_busy:
                                # Update availability_status to indicate Google Calendar conflict
                                if time_slot.get("availability_status") == "OK":
                                    time_slot["availability_status"] = "BLOCKED_GOOGLE_CALENDAR"
                                    blocked_count += 1
                                    print(f"Updated {time_slot['available_time']} to BLOCKED_GOOGLE_CALENDAR")
                    
                    print(f"=== INTEGRATION SUMMARY ===")
                    print(f"Total time slots checked: {len(available_times['result'])}")
                    print(f"Time slots blocked by Google Calendar: {blocked_count}")
                    print(f"Time slots remaining available: {len(available_times['result']) - blocked_count}")
                    
                    # Check if all times were blocked after Google Calendar processing
                    available_count = len([slot for slot in available_times['result'] if slot.get('availability_status') == 'OK'])
                    if available_count == 0 and len(available_times['result']) > 0:
                        print("All time slots are blocked - no availability")
                        available_times["message"] = "No available time slots found for the selected date. All times are currently blocked. Please try a different date or contact the practitioner directly."
                        available_times["no_availability"] = True
                else:
                    print("No FreeBusy data available - continuing with original availability status")
                    print("This could be due to:")
                    print("  - User 100-000093 not found")
                    print("  - No valid Google tokens")
                    print("  - Google Calendar API error")
            else:
                print("No result key in response")
            # print("Available Times: ", str(available_times['result'][0]["appt_start"]))

            return available_times

        except Exception as e:
            print(f"Error in AvailableAppointments: {str(e)}")
            raise BadRequest(
                f"Available Time Request failed: {str(e)}")
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

            response["message"] = "successful"

            return response, 200
        except:
            raise BadRequest("Request failed, please try again later.")
        finally:
            disconnect(conn)


class GooglecalendarEvents(Resource):
    def post(self, customer_uid, start, end):
        print("In Google calendar Events")
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
                print("in if")
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


def get_freebusy_data(customer_uid, start_date, end_date):
    """
    Get FreeBusy data for a customer from Google Calendar API
    Returns busy times in Pacific Time
    """
    try:
        # Get user tokens
        conn = connect()
        items = execute(
            """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
            + customer_uid
            + """\'""",
            "get",
            conn,
        )
        
        if len(items["result"]) == 0:
            print("No user found for FreeBusy check")
            return None
            
        print("FreeBusy - Retrieved user tokens")
        
        # Check if tokens need refreshing (same logic as GoogleFreeBusy endpoint)
        needs_refresh = (
            items["result"][0]["access_expires_in"] == None
            or items["result"][0]["social_timestamp"] == None
            or items["result"][0]["user_refresh_token"] == None
        )
        
        print(f"FreeBusy - Initial needs_refresh: {needs_refresh}")
        print(f"FreeBusy - access_expires_in: {items['result'][0]['access_expires_in']}")
        print(f"FreeBusy - social_timestamp: {items['result'][0]['social_timestamp']}")
        print(f"FreeBusy - user_refresh_token: {items['result'][0]['user_refresh_token'][:20] if items['result'][0]['user_refresh_token'] else 'None'}...")
        
        if not needs_refresh:
            # Check if existing tokens are still valid
            from datetime import datetime
            try:
                access_issue_min = int(items["result"][0]["access_expires_in"]) / 60
                social_timestamp = datetime.strptime(
                    items["result"][0]["social_timestamp"], "%Y-%m-%d %H:%M:%S"
                )
                current_timestamp = datetime.strptime(getNow(), "%Y-%m-%d %H:%M:%S")
                diff = (current_timestamp - social_timestamp).total_seconds() / 60
                
                print(f"FreeBusy - Token age: {diff} minutes, expires in: {access_issue_min} minutes")
                
                if int(diff) > int(access_issue_min):
                    needs_refresh = True
                    print("FreeBusy - Tokens expired, need refresh")
                else:
                    print("FreeBusy - Tokens still valid, no refresh needed")
            except Exception as e:
                print(f"FreeBusy - Error checking token validity: {e}")
                needs_refresh = True
        
        if needs_refresh:
            print("FreeBusy - Refreshing tokens...")
            try:
                if items["result"][0]["user_refresh_token"] is None:
                    print("FreeBusy - No refresh token available")
                    return None
                
                f = open("credentials.json")
                data = json.load(f)
                client_id = data["web"]["client_id"]
                client_secret = data["web"]["client_secret"]
                
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items["result"][0]["user_refresh_token"],
                }
                
                authorization_url = "https://accounts.google.com/o/oauth2/token"
                print(f"FreeBusy - Refreshing token with URL: {authorization_url}")
                print(f"FreeBusy - Refresh params: {params}")
                
                r = requests.post(authorization_url, data=params)
                print(f"FreeBusy - Token refresh response status: {r.status_code}")
                
                if r.ok:
                    response_data = r.json()
                    auth_token = response_data.get("access_token")
                    expires_in = response_data.get("expires_in")
                    
                    if not auth_token or not expires_in:
                        print(f"FreeBusy - Invalid token refresh response: {response_data}")
                        return None
                    
                    print(f"FreeBusy - New access token: {auth_token[:20]}...")
                    print(f"FreeBusy - Token expires in: {expires_in} seconds")
                    
                    execute(
                        """UPDATE customers SET
                                    user_access_token = \'"""
                        + str(auth_token)
                        + """\'
                                    , social_timestamp = \'"""
                        + str(getNow())
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
                    
                    # Get updated tokens
                    items = execute(
                        """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
                        + customer_uid
                        + """\'""",
                        "get",
                        conn,
                    )
                    print("FreeBusy - Tokens refreshed successfully")
                else:
                    print(f"FreeBusy - Failed to refresh tokens: {r.status_code}")
                    print(f"FreeBusy - Error response: {r.text}")
                    return None
            except Exception as e:
                print(f"FreeBusy - Error refreshing tokens: {e}")
                return None
            
        # Validate access token before making API call
        access_token = items['result'][0]['user_access_token']
        if not access_token or access_token == 'None' or access_token == '':
            print("FreeBusy - No valid access token available")
            return None
            
        print(f"FreeBusy - Using access token: {access_token[:20]}...")
        
        # Test the token with a simple API call first
        print("FreeBusy - Testing token validity...")
        test_url = "https://www.googleapis.com/calendar/v3/calendars/primary"
        test_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        test_response = requests.get(test_url, headers=test_headers)
        print(f"FreeBusy - Token test response status: {test_response.status_code}")
        
        if test_response.status_code == 401:
            print("FreeBusy - Token is invalid, forcing refresh...")
            # Force token refresh
            try:
                f = open("credentials.json")
                data = json.load(f)
                client_id = data["web"]["client_id"]
                client_secret = data["web"]["client_secret"]
                
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items["result"][0]["user_refresh_token"],
                }
                
                authorization_url = "https://accounts.google.com/o/oauth2/token"
                print(f"FreeBusy - Forcing token refresh...")
                
                r = requests.post(authorization_url, data=params)
                print(f"FreeBusy - Forced refresh response status: {r.status_code}")
                
                if r.ok:
                    response_data = r.json()
                    auth_token = response_data.get("access_token")
                    expires_in = response_data.get("expires_in")
                    
                    if auth_token and expires_in:
                        print(f"FreeBusy - New access token: {auth_token[:20]}...")
                        
                        execute(
                            """UPDATE customers SET
                                        user_access_token = \'"""
                            + str(auth_token)
                            + """\'
                                        , social_timestamp = \'"""
                            + str(getNow())
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
                        
                        # Update access_token for this request
                        access_token = auth_token
                        print("FreeBusy - Token refreshed successfully")
                    else:
                        print("FreeBusy - Invalid refresh response")
                        return None
                else:
                    print(f"FreeBusy - Token refresh failed: {r.status_code}")
                    print(f"FreeBusy - Error: {r.text}")
                    return None
            except Exception as e:
                print(f"FreeBusy - Error during forced refresh: {e}")
                return None
        elif test_response.status_code != 200:
            print(f"FreeBusy - Token test failed with status: {test_response.status_code}")
            return None
        else:
            print("FreeBusy - Token is valid")
        
        # Use tokens to fetch FreeBusy information
        print("FreeBusy - Making FreeBusy API request...")
        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        body = {
            "timeMin": start_date,
            "timeMax": end_date,
            "items": [{"id": "primary"}]
        }
        
        print(f"FreeBusy - Request body: {body}")
        response = requests.post(url, headers=headers, data=json.dumps(body))
        print(f"FreeBusy - Response status: {response.status_code}")
        
        if response.status_code == 200:
            freebusy_data = response.json()
            print("FreeBusy - API call successful")
            # Convert to Pacific Time
            pacific_data = convert_to_pacific_time(freebusy_data)
            return pacific_data
        else:
            print(f"FreeBusy API error: {response.status_code}")
            print(f"FreeBusy API error response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting FreeBusy data: {e}")
        return None
    finally:
        disconnect(conn)


def convert_to_pacific_time(freebusy_data):
    """
    Convert UTC times in Google FreeBusy response to Pacific Time
    """
    import pytz
    from datetime import datetime
    
    try:
        # Create timezone objects
        utc = pytz.UTC
        pacific = pytz.timezone('US/Pacific')
        
        # Convert the main timeMin and timeMax
        if 'timeMin' in freebusy_data:
            utc_time = datetime.fromisoformat(freebusy_data['timeMin'].replace('Z', '+00:00'))
            pacific_time = utc_time.astimezone(pacific)
            freebusy_data['timeMin'] = pacific_time.isoformat()
            
        if 'timeMax' in freebusy_data:
            utc_time = datetime.fromisoformat(freebusy_data['timeMax'].replace('Z', '+00:00'))
            pacific_time = utc_time.astimezone(pacific)
            freebusy_data['timeMax'] = pacific_time.isoformat()
        
        # Convert busy times in each calendar
        if 'calendars' in freebusy_data:
            for calendar_id, calendar_data in freebusy_data['calendars'].items():
                if 'busy' in calendar_data:
                    for busy_period in calendar_data['busy']:
                        # Convert start time
                        if 'start' in busy_period:
                            utc_time = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                            pacific_time = utc_time.astimezone(pacific)
                            busy_period['start'] = pacific_time.isoformat()
                        
                        # Convert end time
                        if 'end' in busy_period:
                            utc_time = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                            pacific_time = utc_time.astimezone(pacific)
                            busy_period['end'] = pacific_time.isoformat()
        
        return freebusy_data
        
    except Exception as e:
        print(f"Error converting to Pacific Time: {e}")
        # Return original data if conversion fails
        return freebusy_data


def filter_busy_periods_for_date(freebusy_data, appointment_date):
    """
    Filter busy periods to only include those on the appointment date
    Returns a list of busy periods for the specific date
    """
    try:
        from datetime import datetime
        import pytz
        
        pacific = pytz.timezone('US/Pacific')
        appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        appointment_busy_periods = []
        
        for calendar_id, calendar_data in freebusy_data['calendars'].items():
            if 'busy' in calendar_data:
                for busy_period in calendar_data['busy']:
                    if 'start' in busy_period and 'end' in busy_period:
                        # Parse busy period times
                        busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                        
                        # Convert to Pacific Time
                        busy_start_pacific = busy_start.astimezone(pacific)
                        busy_end_pacific = busy_end.astimezone(pacific)
                        
                        # Only include busy periods on the appointment date
                        if busy_start_pacific.date() == appointment_date_obj:
                            appointment_busy_periods.append({
                                'start': busy_start_pacific,
                                'end': busy_end_pacific
                            })
        
        return appointment_busy_periods
        
    except Exception as e:
        print(f"Error filtering busy periods: {e}")
        return []


def is_time_slot_busy_optimized(time_slot_start, time_slot_end, appointment_busy_periods, appointment_date):
    """
    Check if a time slot conflicts with pre-filtered busy periods for the appointment date
    Returns True if busy, False if available
    """
    try:
        if not appointment_busy_periods:
            return False
            
        # Convert time slot to datetime objects for comparison
        from datetime import datetime
        import pytz
        
        pacific = pytz.timezone('US/Pacific')
        
        # Parse time slot times (assuming they're in format like "09:00 AM")
        time_slot_start_dt = datetime.strptime(time_slot_start, '%I:%M %p').time()
        time_slot_end_dt = datetime.strptime(time_slot_end, '%I:%M %p').time()
        
        # Use the appointment date for the time slot
        appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        time_slot_start_full = pacific.localize(datetime.combine(appointment_date_obj, time_slot_start_dt))
        time_slot_end_full = pacific.localize(datetime.combine(appointment_date_obj, time_slot_end_dt))
        
        print(f"Checking time slot: {time_slot_start}-{time_slot_end} on {appointment_date}")
        print(f"Time slot full range: {time_slot_start_full} to {time_slot_end_full}")
        
        # Check time slot against pre-filtered busy periods
        for busy_period in appointment_busy_periods:
            busy_start_pacific = busy_period['start']
            busy_end_pacific = busy_period['end']
            
            # Check if time slot overlaps with busy period
            if (time_slot_start_full < busy_end_pacific and time_slot_end_full > busy_start_pacific):
                print(f"Time slot {time_slot_start}-{time_slot_end} on {appointment_date} conflicts with busy period {busy_start_pacific.strftime('%Y-%m-%d %I:%M %p')}-{busy_end_pacific.strftime('%I:%M %p')}")
                return True
            else:
                print(f"Time slot {time_slot_start}-{time_slot_end} on {appointment_date} does NOT conflict with busy period {busy_start_pacific.strftime('%Y-%m-%d %I:%M %p')}-{busy_end_pacific.strftime('%I:%M %p')}")
        
        return False
        
    except Exception as e:
        print(f"Error checking time slot busy status: {e}")
        return False


def create_google_calendar_event(customer_uid, appointment_details):
    """
    Create a Google Calendar event for a new appointment
    """
    try:
        conn = connect()
        
        # Get practitioner's Google Calendar credentials
        items = execute(
            """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
            + customer_uid
            + """\'""",
            "get",
            conn,
        )
        
        if len(items["result"]) == 0:
            print(f"No Google Calendar credentials found for practitioner {customer_uid}")
            return None
            
        print(f"Creating Google Calendar event for practitioner {customer_uid}")
        
        # Check if tokens need refresh
        needs_refresh = (
            items["result"][0]["access_expires_in"] == None
            or items["result"][0]["social_timestamp"] == None
            or items["result"][0]["user_refresh_token"] == None
        )
        
        if not needs_refresh:
            from datetime import datetime
            access_issue_min = int(items["result"][0]["access_expires_in"]) / 60
            social_timestamp = datetime.strptime(
                items["result"][0]["social_timestamp"], "%Y-%m-%d %H:%M:%S"
            )
            current_timestamp = datetime.strptime(getNow(), "%Y-%m-%d %H:%M:%S")
            diff = (current_timestamp - social_timestamp).total_seconds() / 60
            
            if int(diff) > int(access_issue_min):
                needs_refresh = True
                print("Google Calendar tokens expired, refreshing...")
        
        if needs_refresh:
            print("Refreshing Google Calendar tokens...")
            try:
                if items["result"][0]["user_refresh_token"] is None:
                    print("No refresh token available for Google Calendar")
                    return None
                
                f = open("credentials.json")
                data = json.load(f)
                client_id = data["web"]["client_id"]
                client_secret = data["web"]["client_secret"]
                
                params = {
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": items["result"][0]["user_refresh_token"],
                }
                
                authorization_url = "https://accounts.google.com/o/oauth2/token"
                r = requests.post(authorization_url, data=params)
                
                if r.ok:
                    auth_token = r.json()["access_token"]
                    expires_in = r.json()["expires_in"]
                    
                    execute(
                        """UPDATE customers SET
                                    user_access_token = \'"""
                        + str(auth_token)
                        + """\'
                                    , social_timestamp = \'"""
                        + str(getNow())
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
                    print("Google Calendar tokens refreshed successfully")
                else:
                    print(f"Failed to refresh Google Calendar tokens: {r.status_code}")
                    return None
            except Exception as e:
                print(f"Error refreshing Google Calendar tokens: {e}")
                return None
        
        # Create the calendar event
        print("Creating Google Calendar event...")
        
        # Format appointment details for Google Calendar
        from datetime import datetime, timedelta
        import pytz
        
        pacific = pytz.timezone('US/Pacific')
        
        # Parse appointment date and time
        appointment_date = appointment_details['date']
        appointment_time = appointment_details['time']
        duration = appointment_details['duration']
        
        # Create datetime objects
        start_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        start_datetime_pacific = pacific.localize(start_datetime)
        
        # Calculate end time based on duration
        duration_parts = duration.split(':')
        duration_hours = int(duration_parts[0])
        duration_minutes = int(duration_parts[1])
        end_datetime_pacific = start_datetime_pacific + timedelta(hours=duration_hours, minutes=duration_minutes)
        
        # Convert to UTC for Google Calendar API
        start_datetime_utc = start_datetime_pacific.astimezone(pytz.UTC)
        end_datetime_utc = end_datetime_pacific.astimezone(pytz.UTC)
        
        # Format for Google Calendar API
        start_time_iso = start_datetime_utc.isoformat().replace('+00:00', 'Z')
        end_time_iso = end_datetime_utc.isoformat().replace('+00:00', 'Z')
        
        # Create event details
        event_title = f"{appointment_details['treatment_title']} - {appointment_details['customer_name']}"
        event_description = f"""
            Appointment Details:
            • Customer: {appointment_details['customer_name']}
            • Email: {appointment_details['customer_email']}
            • Phone: {appointment_details['customer_phone']}
            • Age: {appointment_details['age']}
            • Gender: {appointment_details['gender']}
            • Mode: {appointment_details['mode']}
            • Notes: {appointment_details['notes']}
            • Price: ${appointment_details['purchase_price']}
                    """.strip()
        
        # Prepare event data
        event_data = {
            "summary": event_title,
            "description": event_description,
            "start": {
                "dateTime": start_time_iso,
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time_iso,
                "timeZone": "UTC"
            },
            "location": appointment_details['location'],
            "reminders": {
                "useDefault": True
            }
        }
        
        # Make API call to create event
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        headers = {
            "Authorization": f"Bearer {items['result'][0]['user_access_token']}",
            "Content-Type": "application/json"
        }
        
        # print(f"Creating event: {event_title}")
        # print(f"Start time: {start_time_iso}")
        # print(f"End time: {end_time_iso}")
        
        response = requests.post(url, headers=headers, data=json.dumps(event_data))
        
        if response.status_code == 200:
            event_result = response.json()
            print(f"Google Calendar event created successfully: {event_result.get('id')}")
            return event_result
        else:
            print(f"Failed to create Google Calendar event: {response.status_code}")
            print(f"Error response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating Google Calendar event: {e}")
        return None
    finally:
        disconnect(conn)


def is_time_slot_busy(time_slot_start, time_slot_end, freebusy_data, appointment_date):
    """
    Check if a time slot conflicts with Google Calendar busy times
    Returns True if busy, False if available
    """
    try:
        if not freebusy_data or 'calendars' not in freebusy_data:
            return False
            
        # Convert time slot to datetime objects for comparison
        from datetime import datetime
        import pytz
        
        pacific = pytz.timezone('US/Pacific')
        
        # Parse time slot times (assuming they're in format like "09:00 AM")
        time_slot_start_dt = datetime.strptime(time_slot_start, '%I:%M %p').time()
        time_slot_end_dt = datetime.strptime(time_slot_end, '%I:%M %p').time()
        
        # Use the appointment date for the time slot (not today's date)
        appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        time_slot_start_full = pacific.localize(datetime.combine(appointment_date_obj, time_slot_start_dt))
        time_slot_end_full = pacific.localize(datetime.combine(appointment_date_obj, time_slot_end_dt))
        
        print(f"Checking time slot: {time_slot_start}-{time_slot_end} on {appointment_date}")
        print(f"Time slot full range: {time_slot_start_full} to {time_slot_end_full}")
        
        # Filter busy periods to only include those on the appointment date
        appointment_busy_periods = []
        for calendar_id, calendar_data in freebusy_data['calendars'].items():
            if 'busy' in calendar_data:
                for busy_period in calendar_data['busy']:
                    if 'start' in busy_period and 'end' in busy_period:
                        # Parse busy period times
                        busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                        
                        # Convert to Pacific Time
                        busy_start_pacific = busy_start.astimezone(pacific)
                        busy_end_pacific = busy_end.astimezone(pacific)
                        
                        # Only check busy periods on the appointment date
                        if busy_start_pacific.date() == appointment_date_obj:
                            appointment_busy_periods.append({
                                'start': busy_start_pacific,
                                'end': busy_end_pacific
                            })
        
        print(f"Found {len(appointment_busy_periods)} busy periods on {appointment_date}")
        
        # Check time slot against busy periods on the appointment date only
        for busy_period in appointment_busy_periods:
            busy_start_pacific = busy_period['start']
            busy_end_pacific = busy_period['end']
            
            # Check if time slot overlaps with busy period
            if (time_slot_start_full < busy_end_pacific and time_slot_end_full > busy_start_pacific):
                print(f"Time slot {time_slot_start}-{time_slot_end} on {appointment_date} conflicts with busy period {busy_start_pacific.strftime('%Y-%m-%d %I:%M %p')}-{busy_end_pacific.strftime('%I:%M %p')}")
                return True
            else:
                print(f"Time slot {time_slot_start}-{time_slot_end} on {appointment_date} does NOT conflict with busy period {busy_start_pacific.strftime('%Y-%m-%d %I:%M %p')}-{busy_end_pacific.strftime('%I:%M %p')}")
        
        return False
        
    except Exception as e:
        print(f"Error checking time slot busy status: {e}")
        return False


class GoogleFreeBusy(Resource):
    def post(self, customer_uid, start, end):
        print("In Google FreeBusy")
        try:
            conn = connect()
            print(customer_uid, start, end)
            timestamp = getNow()
            
            # Convert start and end parameters to proper date format for Google Calendar API
            from datetime import datetime, timedelta
            
            # Handle different input formats
            try:
                # Try to parse as full dates first (YYYY-MM-DD format)
                if len(start) == 10 and len(end) == 10 and start.count('-') == 2 and end.count('-') == 2:
                    # Full date format: 2025-09-14
                    start_date = start + 'T00:00:00Z'
                    end_date = end + 'T23:59:59Z'
                elif start.isdigit() and end.isdigit():
                    # Day numbers: 9, 12 - convert to current month
                    current_date = datetime.now()
                    start_day = int(start)
                    end_day = int(end)
                    start_date = current_date.replace(day=start_day).strftime('%Y-%m-%dT00:00:00Z')
                    end_date = current_date.replace(day=end_day).strftime('%Y-%m-%dT23:59:59Z')
                else:
                    # Assume they're already in the correct format
                    start_date = start
                    end_date = end
                    
                print(f"FreeBusy date range: {start_date} to {end_date}")
            except Exception as e:
                print(f"Error parsing dates: {e}")
                return {"error": f"Invalid date format. Expected YYYY-MM-DD or day numbers, got: {start}, {end}"}

            # Get user tokens
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
            
            # Check if tokens need refreshing
            needs_refresh = (
                items["result"][0]["access_expires_in"] == None
                or items["result"][0]["social_timestamp"] == None
                or items["result"][0]["user_refresh_token"] == None
            )
            
            print(f"GoogleFreeBusy - Initial needs_refresh: {needs_refresh}")
            print(f"GoogleFreeBusy - access_expires_in: {items['result'][0]['access_expires_in']}")
            print(f"GoogleFreeBusy - social_timestamp: {items['result'][0]['social_timestamp']}")
            print(f"GoogleFreeBusy - user_refresh_token: {items['result'][0]['user_refresh_token'][:20] if items['result'][0]['user_refresh_token'] else 'None'}...")
            
            if not needs_refresh:
                # Check if existing tokens are still valid
                try:
                    access_issue_min = int(items["result"][0]["access_expires_in"]) / 60
                    social_timestamp = datetime.strptime(
                        items["result"][0]["social_timestamp"], "%Y-%m-%d %H:%M:%S"
                    )
                    current_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    diff = (current_timestamp - social_timestamp).total_seconds() / 60
                    
                    print(f"GoogleFreeBusy - Token age: {diff} minutes, expires in: {access_issue_min} minutes")
                    
                    if int(diff) > int(access_issue_min):
                        needs_refresh = True
                        print("GoogleFreeBusy - Tokens expired, need refresh")
                    else:
                        print("GoogleFreeBusy - Tokens still valid, no refresh needed")
                except Exception as e:
                    print(f"GoogleFreeBusy - Error checking token validity: {e}")
                    needs_refresh = True
            
            if needs_refresh:
                print("GoogleFreeBusy - Refreshing tokens...")
                try:
                    if items["result"][0]["user_refresh_token"] is None:
                        return {"error": "No refresh token available. User needs to re-authenticate with Google."}
                    
                    f = open("credentials.json")
                    data = json.load(f)
                    client_id = data["web"]["client_id"]
                    client_secret = data["web"]["client_secret"]
                    
                    params = {
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": items["result"][0]["user_refresh_token"],
                    }
                    
                    authorization_url = "https://accounts.google.com/o/oauth2/token"
                    print(f"GoogleFreeBusy - Refreshing token with URL: {authorization_url}")
                    print(f"GoogleFreeBusy - Refresh params: {params}")
                    
                    r = requests.post(authorization_url, data=params)
                    print(f"GoogleFreeBusy - Token refresh response status: {r.status_code}")
                    
                    if r.ok:
                        response_data = r.json()
                        auth_token = response_data.get("access_token")
                        expires_in = response_data.get("expires_in")
                        
                        if not auth_token or not expires_in:
                            print(f"GoogleFreeBusy - Invalid token refresh response: {response_data}")
                            return {"error": "Invalid token refresh response"}
                        
                        print(f"GoogleFreeBusy - New access token: {auth_token[:20]}...")
                        print(f"GoogleFreeBusy - Token expires in: {expires_in} seconds")
                        
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
                        
                        # Get updated tokens
                        items = execute(
                            """SELECT customer_email, user_refresh_token, user_access_token, social_timestamp, access_expires_in FROM customers WHERE customer_uid = \'"""
                            + customer_uid
                            + """\'""",
                            "get",
                            conn,
                        )
                    else:
                        return {"error": "Failed to refresh Google tokens"}
                except Exception as e:
                    return {"error": f"Error refreshing tokens: {str(e)}"}
            
            # Validate access token before making API call
            access_token = items['result'][0]['user_access_token']
            if not access_token or access_token == 'None' or access_token == '':
                print("GoogleFreeBusy - No valid access token available")
                return {"error": "No valid access token available"}
                
            print(f"GoogleFreeBusy - Using access token: {access_token[:20]}...")
            
            # Test the token with a simple API call first
            print("GoogleFreeBusy - Testing token validity...")
            test_url = "https://www.googleapis.com/calendar/v3/calendars/primary"
            test_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            test_response = requests.get(test_url, headers=test_headers)
            print(f"GoogleFreeBusy - Token test response status: {test_response.status_code}")
            
            if test_response.status_code == 401:
                print("GoogleFreeBusy - Token is invalid, forcing refresh...")
                # Force token refresh
                try:
                    f = open("credentials.json")
                    data = json.load(f)
                    client_id = data["web"]["client_id"]
                    client_secret = data["web"]["client_secret"]
                    
                    params = {
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": items["result"][0]["user_refresh_token"],
                    }
                    
                    authorization_url = "https://accounts.google.com/o/oauth2/token"
                    print(f"GoogleFreeBusy - Forcing token refresh...")
                    
                    r = requests.post(authorization_url, data=params)
                    print(f"GoogleFreeBusy - Forced refresh response status: {r.status_code}")
                    
                    if r.ok:
                        response_data = r.json()
                        auth_token = response_data.get("access_token")
                        expires_in = response_data.get("expires_in")
                        
                        if auth_token and expires_in:
                            print(f"GoogleFreeBusy - New access token: {auth_token[:20]}...")
                            
                            execute(
                                """UPDATE customers SET
                                            user_access_token = \'"""
                                + str(auth_token)
                                + """\'
                                            , social_timestamp = \'"""
                                + str(getNow())
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
                            
                            # Update access_token for this request
                            access_token = auth_token
                            print("GoogleFreeBusy - Token refreshed successfully")
                        else:
                            print("GoogleFreeBusy - Invalid refresh response")
                            return {"error": "Invalid refresh response"}
                    else:
                        print(f"GoogleFreeBusy - Token refresh failed: {r.status_code}")
                        print(f"GoogleFreeBusy - Error: {r.text}")
                        return {"error": f"Token refresh failed: {r.text}"}
                except Exception as e:
                    print(f"GoogleFreeBusy - Error during forced refresh: {e}")
                    return {"error": f"Error during forced refresh: {str(e)}"}
            elif test_response.status_code != 200:
                print(f"GoogleFreeBusy - Token test failed with status: {test_response.status_code}")
                return {"error": f"Token test failed with status: {test_response.status_code}"}
            else:
                print("GoogleFreeBusy - Token is valid")
            
            # Use tokens to fetch FreeBusy information
            print("GoogleFreeBusy - Making FreeBusy API request...")
            url = "https://www.googleapis.com/calendar/v3/freeBusy"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            body = {
                "timeMin": start_date,
                "timeMax": end_date,
                "items": [{"id": "primary"}]  # or use customer_email for specific calendar
            }
            
            # print(f"Making FreeBusy request to: {url}")
            # print(f"Request body: {body}")
            
            response = requests.post(url, headers=headers, data=json.dumps(body))
            # print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                freebusy_data = response.json()
                # print(f"FreeBusy response (UTC): {freebusy_data}")
                
                # Convert UTC times to Pacific Time
                pacific_data = convert_to_pacific_time(freebusy_data)
                print(f"FreeBusy response (Pacific): {pacific_data}")
                return pacific_data
            else:
                print(f"Error response: {response.text}")
                return {"error": f"Google FreeBusy API error: {response.status_code}"}

        except Exception as e:
            print(f"Error in GoogleFreeBusy: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
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
        print("In Send EMail CRON")
        try:
            conn = connect()
            recipient = ["pmarathay@gmail.com"]
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
    print("In Send EMail CRON")
    from flask_mail import Mail, Message
    try:
        conn = connect()
        print('here after connect')

        recipient = ["Lmarathay@gmail.com",
                     "pmarathay@gmail.com"]
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
                recipients=["pmarathay@gmail.com"],
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
                recipients=["Lmarathay@gmail.com", "pmarathay@gmail.com"],
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
        # print("\nIn Send EMail get")
        # print(name, age, gender, mode, notes, email, phone, subject)
        response = {}
        try:
            conn = connect()
            subject = subject.split(',')
            # print(subject)
            # print(subject[2])
            # print(subject[2][5:7])

            month_num = subject[2][5:7]
            # print(month_num)
            datetime_object1 = datetime.strptime(month_num, "%m")
            month_name = datetime_object1.strftime("%B")
            # print(month_name)

            day_num = subject[2][8:10]
            # print(day_num)
            # datetime_object2 = datetime.strptime(day_num, "%d")
            datetime_object2 = datetime.strptime(subject[2], "%Y-%m-%d")
            # print(datetime_object2)
            day = datetime_object2.strftime("%A")
            # print(day)
            
            # print(subject[3])
            # time_num = subject[2][0:4]
            # print(time_num)
            datetime_object3 = datetime.strptime(subject[3], "%H:%M")
            time = datetime_object3.strftime("%I:%M %p")
            # print(time)
            phone = phone[0:3] + "-" + phone[3:6] + "-" + phone[6:]
            # print(phone)

            age = age
            gender = gender
            mode = mode
            notes = notes

            # print("Email Info: ", age, gender, time)

            if mode == 'Online':
                location = 'Online - We will send you a Zoom link via email, 5 minutes before the appointment begins'
            else:
                location = '1610 Blossom Hill Rd. Suite 1, San Jose, CA 95124.'
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
            # print("First email sent")

            # Send email to Practitioner
            msg2 = Message(
                "New appointment booked!",
                sender="support@nityaayurveda.com",
                # recipients=[email],
                recipients=["Lmarathay@gmail.com",
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
            # print("Second email sent")

            return "Email Sent", 200

        except:
            raise BadRequest("Request failed mail, please try again later.")
        finally:
            disconnect(conn)

    def post(self):
        print("In Send EMail post")
        try:
            conn = connect()

            data = request.get_json(force=True)
            print(data)
            email = data["email"]
            msg = Message(
                "Thanks for your Email!",
                sender="support@nityaayurveda.com",
                recipients=[email],
                # recipients=[email, "Lmarathay@gmail.com",
                #             "pmarathay@gmail.com"],
            )

            msg.body = (
                "Hi !\n\n"
                "We are looking forward to meeting with you! \n"
                "Email support@nityaayurveda.com if you need to get in touch with us directly.\n"
                "Thank you - Nitya Ayurveda\n\n"
            )
            print('msg-bd----', msg.body)
            print('msg-', msg)
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


                    else:
                        print('AFTER ELSE PHONE CHECK', phone, cust['customer_phone_num'], fuzz.partial_ratio(
                            phone, cust['customer_phone_num']))

                        print('BEFORE ELSE EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                            email, cust['customer_email']))
                        if fuzz.partial_ratio(email, cust['customer_email']) > 90:
                            print('AFTER ELSE EMAIL CHECK', email, cust['customer_email'], fuzz.partial_ratio(
                                email, cust['customer_email']))

                            thresholdEmail.append(cust)


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

api.add_resource(UploadDocument, "/api/v2/uploadDocument")
# api.add_resource(DeleteDocument, "/api/v2/deleteDocument/<string:document_id>")

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
api.add_resource(DeleteTreatment, "/api/v2/deleteTreatment")

api.add_resource(
    GooglecalendarEvents,
    "/api/v2/calendarEvents/<string:customer_uid>,<string:start>,<string:end>",
)
api.add_resource(
    GoogleFreeBusy,
    "/api/v2/freeBusy/<string:customer_uid>,<string:start>,<string:end>",
)
api.add_resource(UpdateAccessToken,
                 "/api/v2/UpdateAccessToken/<string:customer_uid>")
api.add_resource(CustomerToken, "/api/v2/customerToken/<string:customer_uid>")
api.add_resource(
    AvailableAppointments,
    "/api/v2/availableAppointments/<string:date_value>/<string:duration_str>",
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
    app.run(host="127.0.0.1", port=4060)
