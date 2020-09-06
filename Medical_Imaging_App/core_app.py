from flask import Flask, jsonify, request, render_template, flash, redirect, url_for,abort
from flask_cors import CORS
import keras.backend as K
from datetime import datetime as dt
import numpy as np
import cv2
from cv2 import resize, INTER_AREA
import uuid
from PIL import Image
import os
import tempfile
from keras.models import load_model
import imageio
from keras.preprocessing import image
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout, Flatten
from keras.layers import Conv2D
from keras.layers import MaxPooling2D
import keras
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.applications.imagenet_utils import decode_predictions
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import urllib.request
from flask_migrate import Migrate
from string import Template
from flask_login import LoginManager
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin
from flask_login import login_user,logout_user,login_required
from forms import LoginForm,RegistrationForm
import pdfkit
from flask_login import current_user


login_manager = LoginManager()

"""Instantiating the flask object"""
app = Flask(__name__)
CORS(app)


# HTML Template for diplaying the pdf files
HTML_TEMPLATE = Template("""
<iframe src="static/pdf/${place_name}"  width="100%" height="100%"></iframe>
""")


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir,'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)
Migrate(app,db)

login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = os.path.join('static/pdf')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
 return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
  return user.query.get(user_id)

class user(db.Model,UserMixin):

  #__tablename__ = 'users'

  id=db.Column(db.Integer,primary_key=True)
  email=db.Column(db.String(64),unique=True,index=True)
  username=db.Column(db.String(64),unique=True,index=True)
  password_hash=db.Column(db.String(128))
  #ONE TO MANY
  #one doctor many patients
  doctor = db.relationship('Users',backref='name',lazy='dynamic')

  def __init__(self,email,username,password):
    self.email=email
    self.username=username
    self.password_hash=generate_password_hash(password)

  def check_password(self,password):
    return check_password_hash(self.password_hash,password)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patientname = db.Column(db.String(120), index=True, unique=True)
    profile_pic = db.Column(db.String(150))
    doctoruser=db.Column(db.Integer,db.ForeignKey('user.username'))


@app.route('/upload')
def kchkro():
    return render_template('upload.html')

@app.route('/upload1', methods=['POST'])
def upload():
    file = request.files['inputFile']
    patientname = request.form['patientName']
    #doctoruser = request.form['DoctorName']
    filename = secure_filename(file.filename)

    if file and allowed_file(file.filename):
       file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
       newFile = Users(profile_pic=file.filename, patientname=patientname,doctoruser=current_user.username)
       db.session.add(newFile)
       db.session.commit()
       flash('File successfully uploaded ' + file.filename + ' to the database!')
       return redirect('/result')
    else:
       flash('Invalid Upload only txt, pdf, png, jpg, jpeg, gif')
    return redirect('/retino.html')

@app.route('/result')
def result():
    patientlist = Users.query.filter_by(doctoruser=current_user.username)
    print(patientlist)
    return render_template('result.html',patientlist = patientlist)

'''@app.route('/result1')
def result1():
    patientlist = Users.query.all()
    print(patientlist)
    return render_template('result.html',patientlist = patientlist)'''

@app.route('/<some_place>')
def some_place_page(some_place):
    return(HTML_TEMPLATE.substitute(place_name=some_place))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login',methods=['GET','POST'])
def login():
  form=LoginForm()
  if form.validate_on_submit():
    userr = user.query.filter_by(email=form.email.data).first()
    if userr.check_password(form.password.data) and userr is not None:
      login_user(userr)
      flash('Logged In Successfully!')
      next = request.args.get('next')
      if next==None or not next[0]=='/':
        next=url_for('home')

      return redirect(next)
  return render_template('login.html',form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        usser = user(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.create_all()
        db.session.add(usser)
        db.session.commit()
        flash('Thanks for registering! Now you can login!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
  logout_user()
  flash("You just logged out!")
  return redirect(url_for('home'))

@app.route('/checkup')
@login_required
def checkup():
    return render_template('checkup.html')

@app.route('/fun.html')
def fun():
    return render_template('fun.html')

@app.route('/retino.html')
def retino():
    return render_template('retino.html')

@app.route('/oct.html')
def cardiac():
    return render_template('oct.html')

@app.route('/index.html')
def index_from_checkup():
    return render_template('index.html')

@app.route('/checkup.html')
def checkup_from_any():
    return render_template('checkup.html')

@app.route('/blog.html')
def blog():
    return render_template('blog.html')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route("/", methods = ["POST", "GET"])
def index():
  if request.method == "POST":
    type_ = request.form.get("type", None)
    data = None
    final_json = []
    if 'img' in request.files:
      file_ = request.files['img']
      name = os.path.join(tempfile.gettempdir(), str(uuid.uuid4().hex[:10]))
      file_.save(name)
      print("[DEBUG: %s]"%dt.now(),name,file_)

      if(type_=='dia_ret'):
        test_image = Image.open(name)                                  #Read image using the PIL library
        test_image = test_image.resize((128,128), Image.ANTIALIAS)     #Resize the images to 128x128 pixels
        test_image = np.array(test_image)                              #Convert the image to numpy array
        test_image = test_image/255                                    #Scale the pixels between 0 and 1
        test_image = np.expand_dims(test_image, axis=0)                #Add another dimension because the model was trained on (n,128,128,3)
        data = test_image

      elif(type_=='oct'):
       	test_image = imageio.imread(name)                  #Read image using the PIL library
        test_image = resize_image_oct(test_image)          #Resize the images to 128x128 pixels
        test_image = np.array(test_image)                  #Convert the image to numpy array
        test_image = test_image/255                        #Scale the pixels between 0 and 1
        test_image = np.expand_dims(test_image, axis=0)    #Add another dimension because the model was trained on (n,128,128,3)
        data = test_image

      model=get_model(type_)[0]

      if(type_=='dia_ret'):
         preds, pred_val = translate_retinopathy(model["model"].predict_proba(data))
         final_json.append({"empty": False, "type":model["type"],
                            "mild":preds[0],
                            "mod":preds[1],
                            "norm":preds[2],
                            "severe":preds[3],
                            "pred_val": pred_val})
      elif(type_=='oct'):
         preds, pred_val = translate_oct(model["model"].predict(data))
         final_json.append({"empty": False, "type":model["type"],
                            "cnv":preds[0],
                            "dme":preds[1],
                            "drusen":preds[2],
                            "normal":preds[3],
                            "pred_val": pred_val})
    else:
      warn = "Feeding blank image won't work. Please enter an input image to continue."
      pred_val =" "
      final_json.append({"pred_val": warn,"para": " ","unin": " ","tumor": " ", "can":" ",
                         "normal": " ","bac": " ","viral": " ","cnv": " ","dme": " ",
                         "drusen": " ","mild": " ","mod": " ","severe": " ","norm": " ",
                         "top1": " ","top2": " ","top3": " ","top4": " ","top5": " "})

    K.clear_session()
    return jsonify(final_json)
  return jsonify({"empty":True})

"""This function is used to load the model from disk."""
def load_model_(model_name):
  model_name = os.path.join("static/weights",model_name)
  model = load_model(model_name)
  return model

def get_model(name = None):
  model_name = []
  if(name=='dia_ret'):
    model_name.append({"model": load_model_("dia.h5"), "type": name})
  elif(name=='oct'):
    model_name.append({"model": load_model_("cardiac.h5"), "type": name})
  return model_name


def resize_image_oct(image):
    resized_image = cv2.resize(image, (128,128)) #Resize all the images to 128X128 dimensions
    if(len(resized_image.shape)!=3):
        resized_image = cv2.cvtColor(resized_image,cv2.COLOR_GRAY2RGB) #Convert to RGB
    return resized_image

def translate_retinopathy(preds):
  y_proba_Class0 = preds.flatten().tolist()[0] * 100
  y_proba_Class1 = preds.flatten().tolist()[1] * 100
  y_proba_Class2 = preds.flatten().tolist()[2] * 100
  y_proba_Class3 = preds.flatten().tolist()[3] * 100

  mild="Probability of the input image to have Mild Diabetic Retinopathy: {:.2f}%".format(y_proba_Class0)
  mod="Probability of the input image to have Moderate Diabetic Retinopathy: {:.2f}%".format(y_proba_Class1)
  norm="Probability of the input image to be Normal: {:.2f}%".format(y_proba_Class2)
  severe="Probability of the input image to have Severe Diabetic Retinopathy: {:.2f}%".format(y_proba_Class3)

  total = [mild,mod,norm,severe]

  list_proba = [y_proba_Class0,y_proba_Class1,y_proba_Class2,y_proba_Class3]
  statements = ["Inference: The image has high evidence for Mild Nonproliferative Diabetic Retinopathy Disease.",
               "Inference: The image has high evidence for Moderate Nonproliferative Diabetic Retinopathy Disease.",
               "Inference: The image has no evidence for Nonproliferative Diabetic Retinopathy Disease.",
               "Inference: The image has high evidence for Severe Nonproliferative Diabetic Retinopathy Disease."]

  index = list_proba.index(max(list_proba))
  prediction = statements[index]

  return total, prediction


def translate_oct(preds):
  y_proba_Class0 = preds.flatten().tolist()[0] * 100
  y_proba_Class1 = preds.flatten().tolist()[1] * 100
  y_proba_Class2 = preds.flatten().tolist()[2] * 100
  y_proba_Class3 = preds.flatten().tolist()[3] * 100


  cnv="Probability of the input image to have Hyperdynamic Circulation: {:.2f}%".format(y_proba_Class0)
  dme="Probability of the input image to have Normal Ejection Fraction: {:.2f}%".format(y_proba_Class1)
  drusen="Probability of the input image to have Moderate Ejection Fraction: {:.2f}%".format(y_proba_Class2)
  normal="Probability of the input image to have Severe Ejection Fraction: {:.2f}%".format(y_proba_Class3)

  total = [cnv,dme,drusen,normal]

  list_proba = [y_proba_Class0,y_proba_Class1,y_proba_Class2,y_proba_Class3]
  statements = ["Inference: The image has high evidence of Hyperdynamic circular.",
               "Inference: The image has high evidence of Normal Ejection Fraction.",
               "Inference: The image has high evidence of Mild Ejection Fraction .",
               "Inference: The image has high evidence of Moderate Ejection Fraction."]


  index = list_proba.index(max(list_proba))
  prediction = statements[index]

  return total, prediction

def before_request():
    app.jinja_env.cache = {}

if __name__=="__main__":
  app.before_request(before_request)
  app.run("127.0.0.1",5000, debug = False)
