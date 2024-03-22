from datetime import datetime
from enum import Enum
from functools import wraps
import json
from flask import abort, redirect, session, url_for
from bson import ObjectId, json_util
import os

from project import db

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = APP_ROOT + "/static"


def parse_json(data):
    return json.loads(json_util.dumps(data))


# enums
class BlogStatus(Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


# blog template content
def getRoomsWithBlogCount():
    roomList = db.rooms.aggregate(
        [
            {"$match": {"is_active": True}},
            {
                "$lookup": {
                    "from": db.blogs.name,
                    "localField": "_id",
                    "foreignField": "room_id",
                    "pipeline": [{"$match": {"status": BlogStatus.APPROVED.value}}],
                    "as": "blogs",
                }
            },
            {
                "$project": {
                    "room_name": "$room_name",
                    "blog_count": {"$size": "$blogs"},
                }
            },
        ]
    )
    return roomList


# get Featured Blogs
def getFeaturedBlogs():
    blogs = db.blogs.aggregate(
        [
            {"$match": {"is_featured": True}},
            {
                "$lookup": {
                    "from": db.students.name,
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "student",
                }
            },
            {
                "$lookup": {
                    "from": db.rooms.name,
                    "localField": "room_id",
                    "foreignField": "_id",
                    "as": "rooms",
                }
            },
            {"$sort": {"_id": -1}},
            {"$limit": 5},
        ]
    )
    return blogs


# get Featured Blogs
def getMostViewedBlogs():
    blogs = db.blogs.aggregate(
        [
            {"$match": {"status": BlogStatus.APPROVED.value}},
            {
                "$lookup": {
                    "from": db.students.name,
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "student",
                }
            },
            {
                "$lookup": {
                    "from": db.rooms.name,
                    "localField": "room_id",
                    "foreignField": "_id",
                    "as": "rooms",
                }
            },
            {"$sort": {"visit_count": -1}},
            {"$limit": 4},
        ]
    )
    return blogs


# get students list
def getAllStudents():
    return db.students.find({"is_active": True})


# get students list
def getAllRooms():
    return db.rooms.find({"is_active": True})


# return all template datas
def getTemplateDatas():
    template_data = {
        "str": str,
        "roomswithcount": getRoomsWithBlogCount(),
        "featured_blogs": getFeaturedBlogs(),
        "most_viewed_blogs": getMostViewedBlogs(),
        "students": getAllStudents(),
        "rooms": getAllRooms(),
    }
    return template_data


# Session
def start_session(user):
    session["logged_in"] = True
    del user["password"]
    # user['_id'] = str(user['_id'])
    session["user"] = parse_json(user)


# Decorators
def login_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return fn(*args, **kwargs)
        else:
            return redirect("/")

    return wrap


def admin_only(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if session["user"]["role"] == "admin":
            return fn(*args, **kwargs)
        else:
            return abort(403, "You are not authorized to view this page")

    return wrap


def owner_only(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if session["user"]["role"] == "restaurant":
            return fn(*args, **kwargs)
        else:
            return abort(403, "You are not authorized to view this page")

    return wrap


def user_only(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if "role" in session:
            return fn(*args, **kwargs)
        else:
            return abort(403, "You are not authorized to view this page")

    return wrap


def generateUniqueId():
    now = datetime.now()
    dt = now.strftime("%Y%m%d%H%M%S")
    return dt


def getCurrentUserId():
    return session["user"]["_id"]["$oid"]
