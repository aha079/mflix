from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from bson.errors import InvalidId
from sys import maxsize
from datetime import datetime
from os import environ


try: 
    db = MongoClient(environ["MFLIX_DB_URI"])["mflix"]
except KeyError:
    raise Exception("You haven't configured your MFLIX_DB_URI!")

'''
Returns a cursor to a list of MongoDB movies.
Based on the page or the entries per page,
    the result will be skipped and limited.

Returns 2 elements in a tuple:
    (movies, total_num_movies)
'''
def get_movies(filters, page, movies_per_page):
    sort_key = "tomatoes.viewer.numReviews"

    # first collect all movies based on passed filters
    if "$text" in filters:
        score_meta_doc = { "$meta": "textScore" }
        movies = db.movies_initial.find(filters, { "score": score_meta_doc }) \
                          .sort([("score", score_meta_doc)])
    else:
        movies = db.movies_initial.find(filters) \
                          .sort(sort_key, DESCENDING)

    # count number of total movie documents
    total_num_movies = db.movies_initial.count(filters)

    # limit records based on page number
    movies = movies.skip(movies_per_page * page) \
                   .limit(movies_per_page)

    return (movies, total_num_movies)

'''
Returns a MongoDB movie given an ID.
'''
def get_movie(id):
    try:
        return db.movies_initial.find_one({"_id": ObjectId(id)})
    except InvalidId:
        return None

'''
Returns list of all genres in the database.
'''
def get_all_genres():
    return list(db.movies_initial.aggregate([
        {"$unwind": "$genres"},
        {"$project": {"_id": 0, "genres": 1}},
        {"$group": {"_id": None, "genres": {"$addToSet": "$genres"}}}
    ]))[0]["genres"]

'''
Returns a MongoDB user given an email.
'''
def get_user(email):
    return db.users.find_one({"email": email})

'''
Takes in the three required fields needed to add a user,
    and adds one to MongoDB.
'''
def add_user(name, email, hashedpw):
    try:
        db.users.insert_one({"name": name, "email": email, "pw": hashedpw})
        return {"success": True}
    except DuplicateKeyError:
        return {"error": "A user with the given email already exists."}

'''
Takes in the three required fields needed to add a user,
    and adds one to MongoDB.
'''
def add_comment_to_movie(movieid, user, comment, date):
    MOVIE_COMMENT_CACHE_LIMIT = 10

    comment_doc = {
        "name": user.name,
        "email": user.email,
        "movie_id": movieid,
        "text": comment,
        "date": date
    }

    movie = get_movie(movieid)
    if movie:
        update_doc = {
            "$inc": {
                "num_mflix_comments": 1
            },
            "$push": {
                "comments": {
                    "$each": [comment_doc],
                    "$sort": {"date": -1},
                    "$slice": MOVIE_COMMENT_CACHE_LIMIT
                }
            }
        }

        # let's set an `_id` for the comments collection document
        comment_doc["_id"] = "{0}-{1}-{2}".format(movieid, user.name, \
            date.timestamp())

        db.comments.insert_one( comment_doc )

        db.movies_initial.update_one({"_id": ObjectId(movieid)}, update_doc)

'''
Takes in the two required fields needed to remove a comment,
    and removes it from the appropriate places
'''
def delete_comment_from_movie(movieid, commentid):
    db.comments.delete_one({"_id": commentid})

    movie = db.movies_initial.find_one({"_id": ObjectId(movieid)})

    # check to see if the comment is on the movie doc too
    movie = db.movies_initial.find_one({"comments._id": commentid})

    # regardless, decrement the count
    update_doc = {
        "$inc": {
            "num_mflix_comments": -1
        }
    }

    # if so, query to find new list of comments, update the movie doc with
    # them, and decrement the count
    if movie:
        embedded_comments = db.comments.find({"movie_id": ObjectId(movieid)}) \
                                 .sort("date", DESCENDING) \
                                 .limit(10)
        update_doc["$set"] = {"comments": list(embedded_comments)}

    db.movies_initial.update_one({"_id": ObjectId(movieid)}, update_doc)

'''
Returns all comments from just the comments collection given a movie ID.
'''
def get_movie_comments(id):
    try:
        return db.comments.find({"movie_id": ObjectId(id)}) \
                          .sort("date", DESCENDING)
    except InvalidId:
        return None
