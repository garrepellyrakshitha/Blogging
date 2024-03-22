from datetime import datetime
import os
import pathlib
import re
from bson import ObjectId
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from project.others import (
    APP_ROOT,
    BlogStatus,
    getCurrentUserId,
    getFeaturedBlogs,
    getRoomsWithBlogCount,
    getTemplateDatas,
    login_required,
    parse_json,
    start_session,
)
from project import db


student = Blueprint("student", __name__)


@student.route("/")
def index():
    recently_added_blogs = db.blogs.aggregate(
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
            {"$sort": {"_id": -1}},
            {"$limit": 6},
        ]
    )

    featured_blogs = db.blogs.aggregate(
        [
            {"$match": {"is_featured": True, "status": BlogStatus.APPROVED.value}},
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
        ]
    )

    template_datas = getTemplateDatas()
    return render_template(
        "/student/index.html",
        recently_added_blogs=recently_added_blogs,
        featured_blogs=featured_blogs,
        template_datas=template_datas,
    )


@student.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        values = {
            "room_id": ObjectId(request.form.get("room_id")),
            "full_name": request.form.get("full_name"),
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "mobile_no": request.form.get("mobile_no"),
            "role": "student",
            "is_active": True,
        }
        result = db.students.insert_one(values)
        student_id = result.inserted_id
        student = db.students.find_one({"_id": ObjectId(student_id)})
        start_session(student)
        flash("Registered Successfully", "success")
        return redirect(url_for("student.home"))

    rooms = db.rooms.find({"is_active": True})
    return render_template("/student/register.html", rooms=rooms)


@student.route("/login/", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        values = {
            "email": request.form.get("email"),
            "password": request.form.get("password"),
        }
        student = db.students.find_one(values)
        if student:
            if student["is_active"]:
                start_session(student)
                return redirect(url_for("student.home"))
            else:
                msg = "Your login has been disabled contact admin"
        else:
            msg = "Invalid login credentials"

    return render_template("/student/login.html", msg=msg)


@student.route("/home/")
def home():
    student_name = session["user"]["full_name"]
    room = db.rooms.find_one(
        {"_id": ObjectId(session["user"]["room_id"]["$oid"])},
        {"_id": 0, "room_name": 1},
    )

    user_id = getCurrentUserId()
    blogs = db.blogs.find({"author": ObjectId(user_id)})
    blogs = db.blogs.aggregate(
        [
            {"$match": {"author": ObjectId(user_id)}},
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
        ]
    )
    return render_template(
        "/student/home.html",
        student_name=student_name,
        room=room,
        BlogStatus=BlogStatus,
        blogs=blogs,
    )


# student profile view and update
@student.route("/my-profile/", methods=["GET", "POST"])
def profile():
    user_id = getCurrentUserId()

    if request.method == "POST":
        email = request.form.get("email")
        # check if email exist on other student details
        is_exist = db.students.find_one(
            {"_id": {"$nin": [ObjectId(user_id)]}, "email": email}
        )
        if not is_exist:
            values = {
                "full_name": request.form.get("full_name"),
                "email": email,
                "mobile_no": request.form.get("mobile_no"),
            }
            result = db.students.update_one(
                {"_id": ObjectId(user_id)}, {"$set": values}
            )
            if result.modified_count > 0:
                user = db.students.find_one({"_id": ObjectId(user_id)})
                start_session(user)
                flash("Profile updated successfully", "success")
            else:
                flash("No changes made", "info")
        else:
            # if email exist on other student details
            flash("sorry! email already exist", "warning")

        return redirect(url_for("student.profile"))

    user = db.students.find_one({"_id": ObjectId(user_id)})

    return render_template("/student/profile.html", user=user)


# change password
@student.route("/change-password/", methods=["GET", "POST"])
def change_password():
    user_id = getCurrentUserId()
    if request.method == "POST":
        password = request.form.get("password")
        result = db.students.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"password": password}}
        )
        if result.modified_count > 0:
            flash("Password updated successfully", "success")

    return render_template("/student/change_password.html")


@student.route("/my-blogs/")
def student_blogs():
    user_id = getCurrentUserId()
    blogs = db.blogs.find({"author": ObjectId(user_id)})
    return render_template("/student/blogs.html", blogs=blogs, BlogStatus=BlogStatus)


# add or edit blog
@student.route("/add-blog/")
@student.route("/edit-blog/")
def blog_form():
    blog = ""
    room_id = session["user"]["room_id"]["$oid"]
    room = db.rooms.find_one({"_id": ObjectId(room_id)})

    # edit blog
    blog_id = request.args.get("bid")
    if blog_id:
        blog = db.blogs.find_one({"_id": ObjectId(blog_id)})

    return render_template("/student/blog_form.html", blog=blog, room=room)


# add or update blog
@student.route("/save-blog/", methods=["POST"])
def save_blog():
    blog_id = request.form.get("blog_id")
    image = request.files.get("blog_image")
    values = {
        "author": ObjectId(session["user"]["_id"]["$oid"]),
        "room_id": ObjectId(request.form.get("room_id")),
        "blog_title": request.form.get("blog_title"),
        "tags": request.form.get("tags").lower(),
        "content": request.form.get("content"),
    }
    if not blog_id:
        # add blog
        id = ObjectId()

        image_extension = pathlib.Path(image.filename).suffix
        image_file_name = str(id) + image_extension

        values["_id"] = id
        values["inserted_date"] = datetime.now()
        values["image_file_name"] = image_file_name
        values["is_approved"] = True
        values["visit_count"] = 0
        values["is_featured"] = False
        values["likes"] = []
        values["dislikes"] = []
        values["is_active"] = True
        values["status"] = BlogStatus.PENDING.value

        result = db.blogs.insert_one(values)
        if result.inserted_id:
            image.save(APP_ROOT + "/images/uploads/blogs/" + image_file_name)

        flash("Blog created successfully", "success")
    else:
        # update blog
        image_file_name = request.form.get("image_file_name")
        if image.filename:
            image_extension = pathlib.Path(image.filename).suffix
            image_file_name = str(blog_id) + image_extension

        values["image_file_name"] = image_file_name
        result = db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$set": values})
        if image.filename:
            image.save(APP_ROOT + "/images/uploads/blogs/" + image_file_name)

        flash("Blog update successfully", "success")
    return redirect(url_for("student.home"))


# view blog
@student.route("/view-blog/")
def view_blog():
    blog_id = request.args.get("bid")
    blog = db.blogs.aggregate(
        [
            {"$match": {"_id": ObjectId(blog_id)}},
            {
                "$lookup": {
                    "from": db.rooms.name,
                    "localField": "room_id",
                    "foreignField": "_id",
                    "as": "room",
                }
            },
            {
                "$lookup": {
                    "from": db.students.name,
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "user",
                }
            },
        ]
    )

    if not blog:
        return abort(404, "Sorry,Blog not found")

    blog = list(blog)

    # update blog visit count
    visit_count = 0
    if "logged_in" in session:
        current_user = getCurrentUserId()
        if str(blog[0]["author"]) != current_user:
            visit_count = blog[0]["visit_count"] + 1
    else:
        visit_count = blog[0]["visit_count"] + 1

    db.blogs.update_one(
        {"_id": ObjectId(blog_id)}, {"$set": {"visit_count": visit_count}}
    )

    # check blog already liked or disliked by this student
    is_liked = False
    is_disliked = False
    if "logged_in" in session:
        student_id = getCurrentUserId()
        for id in blog[0]["likes"]:
            if id["student_id"] == ObjectId(student_id):
                is_liked = True
                break
        for id in blog[0]["dislikes"]:
            if id["student_id"] == ObjectId(student_id):
                is_disliked = True
                break

    template_datas = getTemplateDatas()
    return render_template(
        "/student/blog_view.html",
        blog=blog[0],
        is_liked=is_liked,
        is_disliked=is_disliked,
        template_datas=template_datas,
        getStudentById=db.getStudentById,
    )


# delete blog
@student.route("/delete-blog/")
def delete_blog():
    blog_id = request.args.get("blog_id")
    blog = db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return abort(404, "blog not found")

    os.remove(os.path.join(APP_ROOT + "/images/uploads/blogs", blog["image_file_name"]))
    db.blogs.delete_one({"_id": ObjectId(blog_id)})

    # set is active false in reoprted blogs collection if reported by other students
    db.reported_blogs.update_many(
        {"blog_id": ObjectId(blog_id)}, {"$set": {"is_active": False}}
    )

    flash("Blog deleted successfully", "success")
    return redirect(url_for("student.student_blogs"))


# Resend rejected blogs for approval
@student.route("/resend-blog-approval/")
def resend_blog_approval():
    blog_id = request.args.get("bid")
    result = db.blogs.update_one(
        {"_id": ObjectId(blog_id)}, {"$set": {"status": BlogStatus.PENDING.value}}
    )
    if result.modified_count > 0:
        flash("Blog sent for approval", "success")
    return redirect(url_for("student.student_blogs"))


# view blogs listed by rooms
@student.route("/room/blogs/")
def view_room_blogs():
    room_id = request.args.get("room_id")
    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return abort(404, "Sorry room not found")

    room_blogs = db.blogs.aggregate(
        [
            {
                "$match": {
                    "room_id": ObjectId(room_id),
                    "status": BlogStatus.APPROVED.value,
                }
            },
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
        ]
    )
    room_blogs = list(room_blogs)
    template_datas = getTemplateDatas()
    return render_template(
        "/student/room_blogs.html",
        room_blogs=room_blogs,
        room=room,
        template_datas=template_datas,
    )


# search blogs
@student.route("/search/")
def search_blogs():
    query = request.args.get("q")
    if query:
        rgx = re.compile(".*" + query + ".*", re.IGNORECASE)
        filter = {
            "$or": [{"blog_title": rgx}, {"tags": rgx}],
            "status": BlogStatus.APPROVED.value,
        }
    else:
        filter = {"status": BlogStatus.APPROVED.value}
        title = request.args.get("title")
        if title:
            rgx_title = re.compile(".*" + title + ".*", re.IGNORECASE)
            filter["blog_title"] = rgx_title

        room_id = request.args.get("room")
        if room_id:
            filter["room_id"] = ObjectId(room_id)

        student_id = request.args.get("student")
        if student_id:
            filter["author"] = ObjectId(student_id)

    print(filter)
    blogs = db.blogs.aggregate(
        [
            {"$match": filter},
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
        ]
    )
    blogs = list(blogs)

    template_datas = getTemplateDatas()
    return render_template(
        "/student/search.html", blogs=blogs, template_datas=template_datas
    )


# student like blog
@student.route("/like-blog/", methods=["POST"])
def like_blog():
    blog_id = request.form.get("blog_id")
    student_id = getCurrentUserId()

    # check if student already liked this blog
    like_exist = db.blogs.count_documents(
        {"_id": ObjectId(blog_id), "likes.student_id": ObjectId(student_id)}
    )

    if like_exist == 0:
        # check if student already disliked this blog
        dislike_exist = db.blogs.count_documents(
            {"_id": ObjectId(blog_id), "dislikes.student_id": ObjectId(student_id)}
        )
        if dislike_exist > 0:
            # delete student id from dislike array
            db.blogs.update_one(
                {"_id": ObjectId(blog_id)},
                {"$pull": {"dislikes": {"student_id": ObjectId(student_id)}}},
            )

        # add student id to like array
        result = db.blogs.update_one(
            {"_id": ObjectId(blog_id)},
            {"$push": {"likes": {"student_id": ObjectId(student_id)}}},
        )
        if result.modified_count > 0:
            return jsonify(True)
    return jsonify(False)


# student dislike blog
@student.route("/dislike-blog/", methods=["POST"])
def dislike_blog():
    blog_id = request.form.get("blog_id")
    student_id = getCurrentUserId()

    # check if student already disliked this blog
    dislike_exist = db.blogs.count_documents(
        {"_id": ObjectId(blog_id), "dislikes.student_id": ObjectId(student_id)}
    )

    if dislike_exist == 0:
        # check if student already liked this blog
        like_exist = db.blogs.count_documents(
            {"_id": ObjectId(blog_id), "likes.student_id": ObjectId(student_id)}
        )
        if like_exist > 0:
            # delete student id from like array
            db.blogs.update_one(
                {"_id": ObjectId(blog_id)},
                {"$pull": {"likes": {"student_id": ObjectId(student_id)}}},
            )

        # add student id to dislike array
        result = db.blogs.update_one(
            {"_id": ObjectId(blog_id)},
            {"$push": {"dislikes": {"student_id": ObjectId(student_id)}}},
        )
        if result.modified_count > 0:
            return jsonify(True)
    return jsonify(False)


# add comments
@student.route("/add-comments/", methods=["POST"])
def add_comments():
    student_id = getCurrentUserId()
    blog_id = request.form.get("blog_id")
    comment = request.form.get("comment")
    values = {
        "_id": ObjectId(),
        "student_id": ObjectId(student_id),
        "comment_date": datetime.now(),
        "comment": comment,
    }
    db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$push": {"comments": values}})
    return redirect(url_for("student.view_blog", bid=blog_id))


# add reply to comments
@student.route("/add-comment-reply/", methods=["POST"])
def add_reply():
    student_id = getCurrentUserId()
    blog_id = request.form.get("blog_id")
    comment_id = request.form.get("comment_id")
    reply = request.form.get("reply")
    values = {
        "_id": ObjectId(),
        "student_id": ObjectId(student_id),
        "reply_date": datetime.now(),
        "reply": reply,
    }
    db.blogs.update_one(
        {"_id": ObjectId(blog_id), "comments._id": ObjectId(comment_id)},
        {"$push": {"comments.$.replies": values}},
    )
    return redirect(url_for("student.view_blog", bid=blog_id))


# report blog
@student.route("/report-blog/", methods=["POST"])
def report_blog():
    student_id = getCurrentUserId()
    blog_id = request.form.get("blog_id")
    message = request.form.get("message")
    values = {
        "_id": ObjectId(),
        "student_id": ObjectId(student_id),
        "blog_id": ObjectId(blog_id),
        "reported_date": datetime.now(),
        "message": message,
        "is_active": True,
    }

    # check the current student already reported this blog and delete the previous
    is_reported = db.reported_blogs.find_one(
        {"student_id": ObjectId(student_id), "blog_id": ObjectId(blog_id)}
    )
    if is_reported:
        # delete previously reported
        db.reported_blogs.delete_one(
            {"student_id": ObjectId(student_id), "blog_id": ObjectId(blog_id)}
        )

    # insert report
    db.reported_blogs.insert_one(values)
    flash("Blog Reported Successfully", "success")
    return redirect(url_for("student.view_blog", bid=blog_id))


# report comments
@student.route("/report-comment/", methods=["POST"])
def report_comments():
    student_id = getCurrentUserId()
    blog_id = request.form.get("blog_id")
    comment_id = request.form.get("comment_id")
    reply_id = request.form.get("reply_id")
    message = request.form.get("message")

    # check the current student already reported this comment and delete old report if reported
    filter = {"comment_id": ObjectId(comment_id), "student_id": ObjectId(student_id)}
    if reply_id:
        filter["reply_id"] = ObjectId(reply_id)

    is_reported = db.reported_comments.find_one(filter)
    if is_reported:
        db.reported_comments.delete_one(filter)

    values = {
        "student_id": ObjectId(student_id),
        "blog_id": ObjectId(blog_id),
        "comment_id": ObjectId(comment_id),
        "comment": request.form.get("comment"),
        "reported_date": datetime.now(),
        "message": message,
        "is_active": True,
    }
    if reply_id:
        values["reply_id"] = ObjectId(reply_id)

    db.reported_comments.insert_one(values)
    flash("comment reported successfully", "success")
    return redirect(url_for("student.view_blog", bid=blog_id))


@student.route("/about-us/")
def about_us():
    template_datas = getTemplateDatas()
    return render_template("/student/about_us.html", template_datas=template_datas)


@student.route("/contact-us/")
def contact_us():
    template_datas = getTemplateDatas()
    return render_template("/student/contact_us.html", template_datas=template_datas)


@student.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("student.index"))


@student.route("/is-student-email-exist", methods=["GET"])
def is_user_email_exist():
    email = request.args.get("email")
    student = db.students.find_one({"email": email})
    if student:
        return jsonify(False)
    else:
        return jsonify(True)


@student.route("/ajax-get-room-names/")
def get_room_names_for_menu():
    rooms = db.rooms.find({}, {"room_name": 1})
    rooms = list(rooms)
    return parse_json(rooms)
