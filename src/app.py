"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Post
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token , jwt_required , get_jwt_identity
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
    
#CONFIGURACION AL MODULO DE FLASK
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get("KEY_JW")

MIGRATE = Migrate(app, db)
jwt=JWTManager(app)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/user', methods=['GET'])
def handle_hello():

    response_body = {
        "msg": "Hello, this is your GET /user response "
    }

    return jsonify(response_body), 200

@app.route('/user', methods=['POST'])
def create_user():
    body=request.json
    email=body.get('email', None)
    password=body.get('password', None)

    if email is None or password is None:
        return jsonify({'Error': 'email and password required'}),400

    password_hash= generate_password_hash(password)
    new_user=User(email=email, password=password_hash, is_active=True)

    db.session.add(new_user)
    try:
        db.session.commit()
        return 'User created'
    except Exception as error:
        db.session.rollback()
        return 'an error ocurred'

@app.route("/login",methods=["POST"])
def user_loging():
    body= request.json
    email=body.get("email",None)
    password=body.get("password",None)
    
    if email is None or password is None:
        return jsonify({
            "Error":"All inputs are required"
        }),400
        
    user = User.query.filter_by(email=email).one_or_none()
    if user is None:
        return jsonify({
            "error":"user no found"
        }),404
    
    password_match = check_password_hash(user.password,password)
    
    if not password_match :
        return jsonify({
            "error":"Incorrect password"
        }),401
       
    user_token= create_access_token({
        "id":user.id,
        "email":user.email,
        
    })
        
    return jsonify({
        "token":user_token
    })

@app.route('/post', methods=['POST'])
@jwt_required()
def create_post():
    body=request.json
    description=body.get('description', None)
    src=body.get('src', None)
    user= get_jwt_identity()
    

    if description is None:
        return jsonify({'Error': 'description is required'}),400
    
    current_date=datetime.now()
    new_post=Post(description=description,user_id=user["id"],time=current_date)
    if src:
        new_post.src=src 
    
    db.session.add(new_post)
    try:
        db.session.commit()
        return 'Post created'
    except Exception as error:
        db.session.rollback()
        return 'an error ocurred'

@app.route('/get', methods=['GET'])
@jwt_required()
def get_user():
    user= get_jwt_identity()
    post_filter= Post.query.filter_by(user_id=user["id"]).all()
    user_post=[post.serialize() for post in post_filter]
    return jsonify({'posts': user_post})

@app.route('/post/<int:id>',methods=["DELETE"])
@jwt_required()
def delete_post(id):
    post_filter = Post.query.filter_by(id=id).one_or_none()
    if post_filter is None:
        return jsonify({
            "error":"post not found"
        }),404
    
    user= get_jwt_identity()
    if post_filter.user_id != user["id"]:
        return jsonify({
            "error":"User not allowed for this action"
        }),401   
        
    db.session.delete(post_filter)
    
    try:
        db.session.commit()
        return jsonify({
            "Details":"Post deleted"
        }),200
    except Exception as error:
        return jsonify({
            "Error":"Internal server error"
        }),500

# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
