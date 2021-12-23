from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user

from project import app
from flask import render_template, redirect, url_for ,session, request
import cx_Oracle
from collections import OrderedDict
#import dbconfig
from project.controllers import dbconfig
#import pandas as pd
#from flask_cors import CORS, cross_origin
import json



@app.route('/gbim', methods=['GET','POST'])
@app.route('/gbim/', methods=['GET','POST'])
@app.route('/gbim/index', methods=['GET','POST'])
@login_required
def index():
    data = { 
        "title": "Hello World",
        "body": "Flask simple MVC",
		"page_router":"Home"
    }
    if request.method == 'POST': 
        print(request.files['customFile'])
        MappingFile = request.files['customFile']
        data_xls = pd.read_excel(MappingFile, sheet_name='MAPPING', header = 1).fillna('')         
        #df1 = pd.read_excel(xls, 'Sheet1')
        #return str(sheet_raw.nrows)
        data['nrows'] = 3
        return render_template('index.html', data = data)
		
    #data['isLogin'] = False
    data['userChineseName'] = session['userChineseName']
    return render_template('index.html', data = data)

@app.route('/gbim/smartfr', methods=['GET'])
@login_required
def smartfr():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"SMART FR 決策輔助"
    }
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    #con = cx_Oracle.connect('id_ap/idap123@tnvqintpotldb.cminl.oa:1521/qintpotl', encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    data['userChineseName'] = session['userChineseName']
    
    smart_fr_predict = {} # OrderedDict();	
    #cur.execute("select STATUS,YYYYMM,sum(PREDICT_QTY) from RQ_ADM.GBIM_SMART_FR_PREDICT group by STATUS,YYYYMM order by YYYYMM,STATUS") 
    #cur.execute("select YYYYMM, max(decode(STATUS,'FR',pp)) FR,max(decode(STATUS,'LR',pp)) LR from (select STATUS,YYYYMM,sum(PREDICT_QTY) pp from RQ_ADM.GBIM_SMART_FR_PREDICT group by STATUS,YYYYMM) a group by YYYYMM")
    cur.execute("select YYYYMM, max(decode(WF,'FR-MP',PQ)), max(decode(WF,'FR-EOL',PQ)) ,max(decode(WF,'LR-MP',PQ)),max(decode(WF,'LR-EOL',PQ)) from ( \
                 select STATUS ||'-'||CASE WHEN warranty_fulfill='N' THEN 'MP' ELSE 'EOL' END as wf ,YYYYMM,sum(PREDICT_QTY) pq from RQ_ADM.GBIM_SMART_FR_PREDICT group by STATUS,warranty_fulfill,YYYYMM \
                 ) a group by YYYYMM")	
    c = 0
    for r in cur :
        tmp = {} #OrderedDict() 
        tmp['YYYYMM'] = r[0]
        tmp['FR-MP'] = r[1]
        tmp['FR-EOL'] = r[2] 
        tmp['LR-MP'] = r[3]
        tmp['LR-EOL'] = r[4]
        smart_fr_predict[c] = tmp
        c=c+1
    data['smart_fr_predict'] = smart_fr_predict

    smart_fr_application = {}
    cur.execute("select STATUS, NVL(max(decode(application,'AA-BD4',PQ)),0), NVL(max(decode(application,'AUTO-BD5',PQ)),0), NVL(max(decode(application,'CE',PQ)),0),\
                 NVL(max(decode(application,'IAVM',PQ)),0), NVL(max(decode(application,'MONITOR',PQ)),0), NVL(max(decode(application,'MP',PQ)),0), \
				 NVL(max(decode(application,'NB',PQ)),0),NVL(max(decode(application,'SET_TV',PQ)),0), NVL(max(decode(application,'TABLET',PQ)),0),\
				 NVL(max(decode(application,'TV',PQ)),0) from (\
                 select STATUS,application,sum(PREDICT_QTY) PQ from RQ_ADM.GBIM_SMART_FR_PREDICT GROUP by STATUS,application order by STATUS,application\
                 ) a group by STATUS")	
    c = 0
    for r in cur :
        tmp = {} #OrderedDict() 
        tmp['STATUS'] = r[0]
        tmp['AA-BD4'] = r[1]
        tmp['AUTO-BD5'] = r[2] 
        tmp['CE'] = r[3]
        tmp['IAVM'] = r[4]
        tmp['MONITOR'] = r[5]
        tmp['MP'] = r[6]
        tmp['NB'] = r[7]
        tmp['SET_TV'] = r[8]
        tmp['TABLET'] = r[9]
        tmp['TV'] = r[10]
        smart_fr_application[c] = tmp
        c=c+1
    data['smart_fr_application'] = smart_fr_application
    cur.close()
    con.close()
	
    return render_template('smartfr.html', data = data)

@app.route('/gbim/areaforecast', methods=['GET'])
@login_required
def areaforecast():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"全球不良品區域預測"
    }
    data['userChineseName'] = session['userChineseName']
	 
    return render_template('areaforecast.html', data = data)

@app.route('/gbim/recommend', methods=['GET'])
@login_required
def recommend():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"全球備品庫存推薦"
    }
    data['userChineseName'] = session['userChineseName']
	 
    
    return render_template('recommend.html', data = data)

@app.route('/gbim/safetystock', methods=['GET'])
@login_required
def safetystock():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"維修中心庫存安全量"
    }
    data['userChineseName'] = session['userChineseName']
	 
    
    return render_template('safetystock.html', data = data)

@app.route('/gbim/audit', methods=['GET'])
@login_required
def audit():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"檢核機制"
    }
    data['userChineseName'] = session['userChineseName']
	 
    
    return render_template('audit.html', data = data)

@app.route('/gbim/admin', methods=['GET'])
@login_required
def admin():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"管理者功能"
    }
    data['userChineseName'] = session['userChineseName']
	 
    
    return render_template('admin.html', data = data)	