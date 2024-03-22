from bson import ObjectId
import pymongo


dbClient = pymongo.MongoClient('mongodb+srv://sxk52450:sxk52450@shiva-s-cluster.iwhzjb6.mongodb.net/')
db = dbClient["blog"]

admin = db['admin']
sub_admins = db['sub_admins']
rooms = db['rooms']
blogs = db['blogs']
students = db['students']
reported_blogs = db['reported_blogs']
reported_comments = db['reported_comments']


def getStudentById(id):
  return students.find_one({"_id":ObjectId(id)})

def getBlogById(id):
  return blogs.find_one({"_id":ObjectId(id)})

def getComments(blog_id, comment_id, reply_id):
  if not reply_id:
    blog_comments = blogs.aggregate([
      {"$match":{"_id":ObjectId(blog_id), "comments._id":ObjectId(comment_id)}},
      {
        "$project":{
          "comments":{
            "$filter":{
              "input":"$comments",
              "as":"comment",
              "cond":{"$eq":["$$comment._id", ObjectId(comment_id)]}
            }
          }
        }
      }
    ])

  if reply_id:
    print(comment_id)
    print(reply_id)
    blog_comments = blogs.aggregate([
      {"$match":{"_id":ObjectId(blog_id)}},
      {
        "$project":{
          "comments.replies":{
            "$filter":{
              "input":"$comments.replies._id",
              "as":"reply",
              "cond":{"$eq":["$$reply", ObjectId(reply_id)]}
            }
          }     
        }
      }
    ])
  
  blog_comments = list(blog_comments)
  print(blog_comments)
  return blog_comments[0]["comments"][0]


