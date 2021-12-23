import codecs
import sys
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user
from flask import render_template, redirect, url_for, request,flash,session
from project import app
import requests 
import json
from datetime import timedelta
"""
    Import MOdels
from project.models.Hello import Hello
"""
app.secret_key = 'super secret string'  # Change this!
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

login_manager = LoginManager()

login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = "login"
login_manager.login_message = "Please LOGIN"
login_manager.login_message_category = "info"
class User(UserMixin):
    pass   
	


@app.route('/gbim/login', methods=['GET', 'POST'])
def login():	
    data = {
        'error' : ""	
    }
    if request.method == 'GET':
        return render_template("login.html", data = data)
		
    UserID = request.form['UserID']
    password = request.form['password']
    print(UserID,' ',password)   
    
     
    #if UserID == None or password == None :
    #    data['error'] = "UserID 與 password都要填!"	
    #    return render_template("login.html", data = data)
		
    json_data = CheckAD(UserID,password) 	
    print(json_data)
	
    if json_data["errMsg"] != "" :
        data['error'] = json_data["errMsg"]
        	
        return render_template("login.html", data = data)
    
    session['userChineseName'] = json.loads(json_data['Properties'])['displayname'][0].split()[1]
    session['PERNR'] = json.loads(json_data['Properties'])['employeeid'][0]
    print('PERNR:',session['PERNR']) 
    #如果設置了 session.permanent 為 True，那麽過期時間是31天
    session.permanent = True	
    app.permanent_session_lifetime = timedelta(days=2) #minutes,hours,days
	
    curr_user = User()
    curr_user.id = UserID
    #flash(f'{UserID}！歡迎加入草泥馬訓練家的行列！')
    # 通過Flask-Login的login_user方法登入使用者
    login_user(curr_user)
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC"
    }
    data['isLogin'] = True
    data['UserID'] = UserID
	 
    #return render_template('index.html', data = data)
    return redirect(url_for('index'))

@app.route('/gbim/logout')  
def logout():
    logout_user()
    return redirect(url_for('login'))
	
def CheckAD(UserID,password):
    data = {"UserID": UserID, "password": password}
    response = requests.post('http://inlcnws/InxSSOAuth/api/Auth/CheckAD', json=data)
    #response = requests.post('http://10.56.199.140/InxSSOAuth/api/Auth/CheckAD', json=data)
    json_data = json.loads(response.text)
    return json_data
	
@login_manager.user_loader  
def user_loader(ID):  
    user = User()  
    user.id = ID
    return user  
	
def to_json(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        get_fun = func(*args, **kwargs)
        return json.dumps(get_fun)

    return wrapper		