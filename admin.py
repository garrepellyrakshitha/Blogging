import os
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
from datetime import datetime
from project import db
from project.others import (
    APP_ROOT,
    BlogStatus,
    admin_only,
    getCurrentUserId,
    login_required,
    start_session,
)


admin = Blueprint("admin", __name__)


@admin.route("/admin/", methods=["GET", "POST"])
@admin.route("/admin/login/", methods=["GET", "POST"])
def admin_login():
    msg = ""
    values = ""
    if request.method == "POST":
        values = {"email": request.form["email"], "password": request.form["password"]}

        user = db.admin.find_one(values)
        if not user:
            user = db.sub_admins.find_one(values)
            if not user:
                msg = "Invalid Login Credentials"
                return render_template("/admin/login.html", msg=msg, values=values)
            else:
                if not user["is_active"]:
                    msg = "Login disabled"
                    return render_template("/admin/login.html", msg=msg, values=values)

        start_session(user)
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("/admin/login.html", msg=msg, values=values)


# admin profile
@admin.route("/admin/profile/", methods=["GET", "POST"])
def admin_profile():
    if request.method == "POST":
        id = request.form.get("id")
        values = {
            "full_name": request.form.get("full_name"),
            "mobile_no": request.form.get("mobile_no"),
        }
        if session["user"]["role"] == "admin":
            values["email"] = request.form.get("email")
            db.admin.update_one({}, {"$set": values})
        else:
            db.sub_admins.update_one({"_id": ObjectId(id)}, {"$set": values})

        flash("profile updated successfully", "success")
        return redirect(url_for("admin.admin_profile"))

    if session["user"]["role"] == "admin":
        user = db.admin.find_one({})
    else:
        id = session["user"]["_id"]["$oid"]
        user = db.sub_admins.find_one({"_id": ObjectId(id)})

    return render_template("/admin/profile.html", user=user)


@admin.route("/admin/change-password/", methods=["GET", "POST"])
def admin_change_password():
    if request.method == "POST":
        id = session["user"]["_id"]["$oid"]
        password = request.form.get("password")

        if session["user"]["role"] == "admin":
            result = db.admin.update_one(
                {"_id": ObjectId(id)}, {"$set": {"password": password}}
            )
        else:
            result = db.sub_admins.update_one(
                {"_id": ObjectId(id)}, {"$set": {"password": password}}
            )

        if result.modified_count > 0:
            flash("Password Updated successfully", "success")
        else:
            flash("No changes made", "danger")
        return redirect(url_for("admin.admin_change_password"))

    return render_template("/admin/change_password.html")


@admin.route("/admin/logout/")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))


@admin.route("/admin/dashboard/")
@login_required
def admin_dashboard():
    rooms_count = db.rooms.count_documents({"is_active": True})
    blogs_count = db.blogs.count_documents({})
    students_count = db.students.count_documents({})

    blogs = db.blogs.aggregate(
        [
            {"$match": {"status": BlogStatus.PENDING.value}},
            {
                "$lookup": {
                    "from": db.rooms.name,
                    "localField": "room_id",
                    "foreignField": "_id",
                    "as": "rooms",
                }
            },
            {
                "$lookup": {
                    "from": db.students.name,
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "students",
                }
            },
        ]
    )

    if session["user"]["role"] != "admin":
        rooms_count = db.rooms.count_documents(
            {"sub_admin_id": ObjectId(getCurrentUserId())}
        )

        blogs_count = 0
        students_count = 0
        blogs = []
        rooms = db.rooms.find({"sub_admin_id": ObjectId(getCurrentUserId())})
        for room in rooms:
            # get students count from each room
            count_students = db.students.count_documents(
                {"room_id": ObjectId(room["_id"]), "is_active": True}
            )
            students_count += count_students

            # get blogs count from each room
            count_blogs = db.blogs.count_documents({"room_id": ObjectId(room["_id"])})
            blogs_count += count_blogs

            # get blog by room id
            blog = db.blogs.aggregate(
                [
                    {
                        "$match": {
                            "room_id": ObjectId(room["_id"]),
                            "status": BlogStatus.PENDING.value,
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
                    {
                        "$lookup": {
                            "from": db.students.name,
                            "localField": "author",
                            "foreignField": "_id",
                            "as": "students",
                        }
                    },
                ]
            )
            blog = list(blog)
            blogs.extend(blog)

    dashboard = {
        "rooms_count": rooms_count,
        "blogs_count": blogs_count,
        "students_count": students_count,
    }

    return render_template("/admin/dashboard.html", dashboard=dashboard, blogs=blogs)


# view sub admin list
@admin.route("/admin/sub-admins/")
def admin_view_sub_admins():
    sub_admins = db.sub_admins.find({}).sort([("is_active", -1), ("_id", -1)])
    return render_template("/admin/sub_admins_view.html", sub_admins=sub_admins)


# add or edit sub admins
@admin.route("/admin/add-sub-admin/")
@admin.route("/admin/edit-sub-admin/")
def admin_view_sub_admin_form():
    sub_admin = ""
    if request.args.get("said"):
        # edit sub-admin
        sub_admin_id = request.args.get("said")
        sub_admin = db.sub_admins.find_one({"_id": ObjectId(sub_admin_id)})
        if not sub_admin:
            return abort(404, "Sub admin not found")

    return render_template("/admin/sub_admin_form.html", sub_admin=sub_admin)


@admin.route("/admin/save-sub-admin/", methods=["POST"])
def admin_save_sub_admin():
    sub_admin_id = request.form.get("sub_admin_id")
    values = {
        "full_name": request.form.get("full_name"),
        "email": request.form.get("email"),
        "mobile_no": request.form.get("mobile_no"),
        "password": request.form.get("password"),
    }

    if not sub_admin_id:
        # add sub admin
        values["is_active"] = True
        values["role"] = "sub_admin"
        db.sub_admins.insert_one(values)
        flash("sub admin added successfully", "success")
    else:
        # update sub admin
        result = db.sub_admins.update_one(
            {"_id": ObjectId(sub_admin_id)}, {"$set": values}
        )
        if result.modified_count > 0:
            flash("sub admin updated successfully", "success")
        else:
            flash("No changes made", "warning")

    return redirect(url_for("admin.admin_view_sub_admins"))


# update student active status
@admin.route("/admin/update-sub-admin-status/<id>/<status>/")
def admin_update_sub_admin_status(id, status):
    sub_admin_id = ObjectId(id)
    status = False if status == "1" else True
    db.sub_admins.update_one({"_id": sub_admin_id}, {"$set": {"is_active": status}})
    flash("Active status updated successfully", "success")
    return redirect(url_for("admin.admin_view_sub_admins"))


# delete sub admin
@admin.route("/admin/delete-sub-admin/")
def admin_delete_sub_admin():
    sub_admin_id = request.args.get("said")
    # check if sub admin is assigned with any rooms
    rooms = db.rooms.find_one({"sub_admin_id": ObjectId(sub_admin_id)})
    if rooms:
        flash(
            "This sub admin has been assigned to rooms, please remove from rooms to delete",
            "warning",
        )
        return redirect(url_for("admin.admin_view_sub_admins"))

    result = db.sub_admins.delete_one({"_id": ObjectId(sub_admin_id)})
    if result.deleted_count > 0:
        flash("Deleted Successfully", "success")
        return redirect(url_for("admin.admin_view_sub_admins"))


@admin.route("/admin/rooms/", methods=["GET", "POST"])
@admin.route("/admin/edit-room")
@admin_only
def admin_rooms():
    room = ""
    if request.method == "POST":
        id = request.form.get("room_id")

        values = {
            "room_name": request.form.get("room_name").capitalize(),
            "sub_admin_id": ObjectId(request.form.get("sub_admin_id")),
        }
        if not id:
            # Add Category
            values["is_active"] = True
            db.rooms.insert_one(values)
            flash("room added successfully", "success")
        else:
            # Update Category
            result = db.rooms.update_one({"_id": ObjectId(id)}, {"$set": values})
            if result.modified_count > 0:
                flash("room updated successfully", "success")
            else:
                flash("No changes made", "warning")

        return redirect(url_for("admin.admin_rooms"))

    # Edit room
    if request.args.get("id"):
        room = db.rooms.find_one({"_id": ObjectId(request.args.get("id"))})

    # rooms = db.rooms.find({}).sort("_id", -1)
    rooms = db.rooms.aggregate(
        [
            {"$match": {}},
            {
                "$lookup": {
                    "from": db.sub_admins.name,
                    "localField": "sub_admin_id",
                    "foreignField": "_id",
                    "as": "sub_admin",
                }
            },
            {"$unwind": "$sub_admin"},
            {"$sort": {"_id": -1}},
        ]
    )
    sub_admins = db.sub_admins.find({"is_active": True})
    return render_template(
        "/admin/rooms.html", rooms=rooms, sub_admins=sub_admins, room=room
    )


@admin.route("/admin/delete-room")
def admin_delete_room():
    room_id = request.args.get("id")
    blogs = db.blogs.find({"room_id": ObjectId(room_id)})
    if blogs:
        flash(
            "please delete all the blogs under this room to delete this room", "warning"
        )
    else:
        result = db.rooms.delete_one({"_id": ObjectId(room_id)})
        if result.deleted_count > 0:
            flash("Room Deleted Successfully", "success")
        else:
            flash("Error Deleting Room", "danger")

    return redirect(url_for("admin.admin_rooms"))


# sub admin view rooms
@admin.route("/admin/subadmin-rooms/")
def subadmin_view_rooms():
    sub_admin_id = getCurrentUserId()
    rooms = db.rooms.aggregate(
        [
            {"$match": {"sub_admin_id": ObjectId(sub_admin_id)}},
            {
                "$lookup": {
                    "from": db.students.name,
                    "localField": "_id",
                    "foreignField": "room_id",
                    "as": "students",
                }
            },
            {
                "$lookup": {
                    "from": db.blogs.name,
                    "localField": "_id",
                    "foreignField": "room_id",
                    "as": "blogs",
                }
            },
            {
                "$addFields": {
                    "student_count": {"$size": "$students"},
                    "blog_count": {"$size": "$blogs"},
                }
            },
        ]
    )
    rooms = list(rooms)
    return render_template("/admin/subadmin_rooms.html", rooms=rooms)


# view  blog list
@admin.route("/admin/blogs/")
def admin_view_blogs():
    blogs = []
    if session["user"]["role"] != "admin":
        rooms = db.rooms.find({"sub_admin_id": ObjectId(getCurrentUserId())})
        for room in rooms:
            blog = db.blogs.aggregate(
                [
                    {
                        "$match": {
                            "room_id": ObjectId(room["_id"]),
                            "status": {"$ne": BlogStatus.PENDING.value},
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
                    {
                        "$lookup": {
                            "from": db.students.name,
                            "localField": "author",
                            "foreignField": "_id",
                            "as": "students",
                        }
                    },
                    {"$sort": {"status": 1, "_id": -1}},
                ]
            )
            blog = list(blog)
            blogs.extend(blog)
    else:
        blogs = db.blogs.aggregate(
            [
                {"$match": {"status": {"$ne": BlogStatus.PENDING.value}}},
                {
                    "$lookup": {
                        "from": db.rooms.name,
                        "localField": "room_id",
                        "foreignField": "_id",
                        "as": "rooms",
                    }
                },
                {
                    "$lookup": {
                        "from": db.students.name,
                        "localField": "author",
                        "foreignField": "_id",
                        "as": "students",
                    }
                },
                {"$sort": {"status": 1, "_id": -1}},
            ]
        )

    blogs = list(blogs)
    return render_template("/admin/blogs.html", blogs=blogs, BlogStatus=BlogStatus)


# view rejected blog list
@admin.route("/admin/view-rejected-blogs/")
def admin_view_rejected_blogs():
    blogs = []
    if session["user"]["role"] != "admin":
        rooms = db.rooms.find({"sub_admin_id": ObjectId(getCurrentUserId())})
        for room in rooms:
            blog = db.blogs.aggregate(
                [
                    {
                        "$match": {
                            "room_id": ObjectId(room["_id"]),
                            "status": BlogStatus.REJECTED.value,
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
                    {
                        "$lookup": {
                            "from": db.students.name,
                            "localField": "author",
                            "foreignField": "_id",
                            "as": "students",
                        }
                    },
                    {"$sort": {"_id": -1}},
                ]
            )
            blog = list(blog)
            blogs.extend(blog)
    else:
        blogs = db.blogs.aggregate(
            [
                {"$match": {"status": BlogStatus.REJECTED.value}},
                {
                    "$lookup": {
                        "from": db.rooms.name,
                        "localField": "room_id",
                        "foreignField": "_id",
                        "as": "rooms",
                    }
                },
                {
                    "$lookup": {
                        "from": db.students.name,
                        "localField": "author",
                        "foreignField": "_id",
                        "as": "students",
                    }
                },
                {"$sort": {"_id": -1}},
            ]
        )

    blogs = list(blogs)
    return render_template(
        "/admin/blogs_rejected.html", blogs=blogs, BlogStatus=BlogStatus
    )


# view blog
@admin.route("/admin/view-blog/")
def admin_view_blog():
    blog_id = request.args.get("bid")
    blog = db.blogs.aggregate(
        [
            {"$match": {"_id": ObjectId(blog_id)}},
            {
                "$lookup": {
                    "from": db.rooms.name,
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "category",
                }
            },
            {
                "$lookup": {
                    "from": db.admin.name,
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "admin",
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
    return render_template(
        "/admin/blog_view.html", blog=blog[0], getStudentById=db.getStudentById
    )


# approve blog
@admin.route("/admin/approve-blog/")
def admin_approve_blog():
    blog_id = request.args.get("bid")
    db.blogs.update_one(
        {"_id": ObjectId(blog_id)}, {"$set": {"status": BlogStatus.APPROVED.value}}
    )
    flash("Blog approved successfully", "success")
    return redirect(url_for("admin.admin_view_blog", bid=blog_id))


# reject blog
@admin.route("/admin/reject-blog/")
def admin_reject_blog():
    blog_id = request.args.get("blog_id")
    remarks = request.args.get("remarks")
    values = {
        "status": BlogStatus.REJECTED.value,
        "rejection_remarks": [
            {
                "rejected_on": datetime.now(),
                "rejected_by": ObjectId(getCurrentUserId()),
                "remarks": remarks,
            }
        ],
    }
    result = db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$set": values})
    if result.modified_count > 0:
        flash("Blog rejected successfully", "success")
    return redirect(url_for("admin.admin_view_blog", bid=blog_id))


# set or unset a blog as featured
@admin.route("/admin/set-featured-blog/")
def admin_set_unset_featured_blog():
    blog_id = request.args.get("bid")
    blog = db.blogs.find_one({"_id": ObjectId(blog_id)}, {"is_featured": 1})
    is_featured = not blog["is_featured"]
    result = db.blogs.update_one(
        {"_id": ObjectId(blog_id)}, {"$set": {"is_featured": is_featured}}
    )
    if result.modified_count > 0:
        flash("Featured status updated", "success")
    return redirect(url_for("admin.admin_view_blogs"))


# delete blog
@admin.route("/admin/delete-blog/")
def admin_delete_blog():
    blog_id = request.args.get("blog_id")
    return_url = request.args.get("return_url")
    blog = db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return abort(404, "blog not found")

    os.remove(os.path.join(APP_ROOT + "/images/uploads/blogs", blog["image_file_name"]))
    db.blogs.delete_one({"_id": ObjectId(blog_id)})

    # delete reoprted blogs & reported comments if this blog exist
    db.reported_blogs.delete_many({"blog_id": ObjectId(blog_id)})
    db.reported_comments.delete_many({"blog_id": ObjectId(blog_id)})

    flash("Blog deleted successfully", "success")
    if return_url:
        return redirect(return_url)
    else:
        return redirect(url_for("admin.admin_view_blogs"))


# view students
@admin.route("/admin/students/")
def admin_view_students():
    students = []
    if session["user"]["role"] != "admin":
        rooms = db.rooms.find({"sub_admin_id": ObjectId(getCurrentUserId())})
        for room in rooms:
            studentList = db.students.aggregate(
                [
                    {"$match": {"room_id": ObjectId(room["_id"])}},
                    {
                        "$lookup": {
                            "from": db.rooms.name,
                            "localField": "room_id",
                            "foreignField": "_id",
                            "as": "rooms",
                        }
                    },
                    {"$sort": {"is_active": -1, "_id": -1}},
                ]
            )
            studentList = list(studentList)
            students.extend(studentList)
    else:
        students = db.students.aggregate(
            [
                {"$match": {}},
                {
                    "$lookup": {
                        "from": db.rooms.name,
                        "localField": "room_id",
                        "foreignField": "_id",
                        "as": "rooms",
                    }
                },
                {"$sort": {"is_active": -1, "_id": -1}},
            ]
        )

    students = list(students)
    return render_template("/admin/students.html", students=students)


# update student active status
@admin.route("/admin/update-student-status/<stud_id>/<status>/")
def admin_update_student_status(stud_id, status):
    student_id = ObjectId(stud_id)
    status = False if status == "1" else True
    db.students.update_one({"_id": student_id}, {"$set": {"is_active": status}})
    flash("student active status updated successfully", "success")
    return redirect(url_for("admin.admin_view_students"))


# delete student
@admin.route("/admin/delete-student/")
def admin_delete_student():
    student_id = request.args.get("sid")
    student = db.students.find_one({"_id": ObjectId(student_id)})
    if not student:
        return abort(404, "student not found")

    # delete student
    db.students.delete_one({"_id": ObjectId(student_id)})
    # delete blogs created by this student
    blogs = db.blogs.find({"author": ObjectId(student_id)})
    if blogs:
        for blog in blogs:
            # delete this blog if exist in reported blogs or reported comments collection
            db.reported_blogs.delete_many({"blog_id": ObjectId(blog["_id"])})
            db.reported_comments.delete_many({"blog_id": ObjectId(blog["_id"])})
            # delete this blog
            db.blogs.delete_one({"_id": ObjectId(blog["_id"])})
    flash("Student deleted successfully", "success")
    return redirect(url_for("admin.admin_view_students"))


# view reported blogs with report count
@admin.route("/admin/reported-blogs/")
def admin_view_reported_blogs():
    blogs = []
    if session["user"]["role"] != "admin":
        rooms = db.rooms.aggregate(
            [
                {"$match": {"sub_admin_id": ObjectId(getCurrentUserId())}},
                {
                    "$lookup": {
                        "from": db.blogs.name,
                        "localField": "_id",
                        "foreignField": "room_id",
                        "as": "blogs",
                    }
                },
            ]
        )
        for room in rooms:
            for blog in room["blogs"]:
                rep_blog = db.reported_blogs.aggregate(
                    [
                        {"$match": {"blog_id": ObjectId(blog["_id"])}},
                        {"$group": {"_id": "$blog_id", "report_count": {"$sum": 1}}},
                        {"$sort": {"report_count": -1}},
                    ]
                )
                rep_blog = list(rep_blog)
                blogs.extend(rep_blog)
    else:
        blogs = db.reported_blogs.aggregate(
            [
                {"$match": {"is_active": True}},
                {"$group": {"_id": "$blog_id", "report_count": {"$sum": 1}}},
                {"$sort": {"report_count": -1}},
            ]
        )

    blogs = list(blogs)
    return render_template(
        "/admin/reported_blogs.html",
        blogs=blogs,
        getStudentById=db.getStudentById,
        getBlogById=db.getBlogById,
    )


# view reported blogs details
@admin.route("/admin/view-reported-blogs-details/")
def admin_view_reported_blog_details():
    blog_id = request.args.get("blog_id")
    blog = db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return abort(404, "Blog not found")

    messages = db.reported_blogs.find({"blog_id": ObjectId(blog_id), "is_active": True})
    return render_template(
        "/admin/reported_blog_messages.html",
        blog=blog,
        messages=messages,
        getStudentById=db.getStudentById,
        getBlogById=db.getBlogById,
    )


# admin view reported comments
@admin.route("/admin/reported-comments/")
def admin_view_reported_comments():
    reported_comments = []
    if session["user"]["role"] != "admin":
        rooms = db.rooms.aggregate(
            [
                {"$match": {"sub_admin_id": ObjectId(getCurrentUserId())}},
                {
                    "$lookup": {
                        "from": db.blogs.name,
                        "localField": "_id",
                        "foreignField": "room_id",
                        "as": "blogs",
                    }
                },
            ]
        )
        for room in rooms:
            for blog in room["blogs"]:
                rep_comment = db.reported_comments.aggregate(
                    [
                        {
                            "$match": {
                                "blog_id": ObjectId(blog["_id"]),
                                "is_active": True,
                            }
                        },
                        {
                            "$lookup": {
                                "from": db.blogs.name,
                                "localField": "blog_id",
                                "foreignField": "_id",
                                "as": "blogs",
                            }
                        },
                        {
                            "$lookup": {
                                "from": db.students.name,
                                "localField": "student_id",
                                "foreignField": "_id",
                                "as": "students",
                            }
                        },
                        {"$sort": {"reported_date": -1}},
                    ]
                )
                rep_comment = list(rep_comment)
                reported_comments.extend(rep_comment)
    else:
        reported_comments = db.reported_comments.aggregate(
            [
                {"$match": {"is_active": True}},
                {
                    "$lookup": {
                        "from": db.blogs.name,
                        "localField": "blog_id",
                        "foreignField": "_id",
                        "as": "blogs",
                    }
                },
                {
                    "$lookup": {
                        "from": db.students.name,
                        "localField": "student_id",
                        "foreignField": "_id",
                        "as": "students",
                    }
                },
                {"$sort": {"reported_date": -1}},
            ]
        )
    reported_comments = list(reported_comments)
    return render_template(
        "/admin/reported_comments.html", reported_comments=reported_comments
    )


# delete student comments
@admin.route("/admin/delete-comment/")
def admin_delete_student_comments():
    blog_id = request.args.get("blog_id")
    comment_id = request.args.get("comment_id")
    reply_id = request.args.get("reply_id")

    if not reply_id:
        # delete comment
        result = db.blogs.update_one(
            {"_id": ObjectId(blog_id)},
            {"$pull": {"comments": {"_id": ObjectId(comment_id)}}},
        )
    else:
        result = db.blogs.update_one(
            {"_id": ObjectId(blog_id), "comments._id": ObjectId(comment_id)},
            {"$pull": {"comments.$.replies": {"_id": ObjectId(reply_id)}}},
        )

    if result.modified_count > 0:
        # set is active false in reoprted comments collection if reported by other students
        filter = {"comment_id": ObjectId(comment_id)}
        if reply_id:
            filter["reply_id"] = ObjectId(reply_id)

        db.reported_comments.update_many(filter, {"$set": {"is_active": False}})

        flash("Comment deleted successfully", "success")
        return jsonify(True)

    return jsonify(False)


@admin.route("/is-sub-admin-email-exist")
def check_sub_admin_email_exist():
    email = request.args.get("email")
    sub_admin_id = request.args.get("sub_admin_id")
    if not sub_admin_id:
        sub_admin = db.sub_admins.find_one({"email": email})
        if sub_admin:
            return jsonify(False)
        else:
            return jsonify(True)
    else:
        sub_admin = db.sub_admins.find_one({"email": email})
        if sub_admin:
            # sub_admin = list(sub_admin)
            exist_sub_admin_id = str(sub_admin["_id"])
            if sub_admin_id != exist_sub_admin_id:
                return jsonify(False)
            else:
                return jsonify(True)
        else:
            return jsonify(True)


@admin.route("/is-room-not-exist")
def check_room_not_exist():
    room_name = request.args.get("room_name").capitalize()
    room_id = request.args.get("room_id")
    if not room_id:
        # check while adding room
        room = db.rooms.find_one({"room_name": room_name})
        if room:
            return jsonify(False)
    else:
        # check while updating room
        room = db.rooms.find_one(
            {"room_name": room_name, "_id": {"$ne": ObjectId(room_id)}}
        )
        if room:
            return jsonify(False)

    return jsonify(True)
