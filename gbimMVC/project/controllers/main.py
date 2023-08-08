from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user

from project import app
from flask import render_template, redirect, url_for ,session, request, send_from_directory
import cx_Oracle,pymysql
from collections import OrderedDict
from project.controllers import dbconfig
import pandas as pd 
import json
#from datetime import datetime
from datetime import datetime, date, timezone,timedelta
#from project.config import *
from dateutil.relativedelta import relativedelta 
import os
from os.path import basename
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

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
    data['UserID'] = session['UserID']
    data['userChineseName'] = session['userChineseName']
    return render_template('index.html', data = data)

@app.route('/gbim/sendFile_audit', methods=['GET','POST'])
@login_required
def sendFile_audit():
    data = {}
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    path_result = r'/home/docker/gbimMVC/sendFile/'
    data['UserID'] = session['UserID']
    cur.execute("select max(issue_date) from RQ_ADM.GBIM_ISSUE_DATE")
    max_issue_date = datetime.strptime(cur.fetchone()[0]+'-10', '%Y-%m-%d')    
    issue_date = (max_issue_date - relativedelta(months=3)).strftime('%Y-%m')
    data['from_end'] = issue_date+'~'+max_issue_date.strftime('%Y-%m')
    yyyymm = (max_issue_date - relativedelta(months=3)).strftime('%Y%m') 
    #'+data['from_end']+' as "資料區間",
    cur.execute('select \''+data['from_end']+'\' as "資料區間", a.model_name as "MODEL NAME",a.qty as "ISSUE DATA",NVL(TO_CHAR(b.predict_qty),\'NA\') as "Smart FR",NVL(TO_CHAR(a.qty-b.predict_qty),\'NA\') as "差異",round((a.qty-b.predict_qty)/a.qty,2)*100||\'%\' as "差異百分比",ABS(round((a.qty-b.predict_qty)/a.qty,2)*100)||\'%\' as "差異百分比 絕對值" from (select model_name ,sum(qty) qty from RQ_ADM.GBIM_ISSUE_DATE where issue_date >= :issue_date group by model_name ) a left join (select model_name, sum(predict_qty) predict_qty from RQ_ADM.GBIM_SMART_FR_PREDICT where yyyymm = :yyyymm group by model_name ) b on a.model_name = b.model_name order by a.model_name',{'issue_date':issue_date,'yyyymm':yyyymm})
    columns = [desc[0] for desc in cur.description]
    result = cur.fetchall()
    GBIM_ISSUEDATA_VS_SMARTFR = pd.DataFrame(list(result), columns=columns)
    GBIM_ISSUEDATA_VS_SMARTFR.to_excel(path_result+'GBIM_ISSUEDATA_VS_SMARTFR.xlsx', index=False, encoding='utf-8-sig')
    data_count = len(GBIM_ISSUEDATA_VS_SMARTFR.index)
    data['size'] = data_count
    
    send_from = "jacob.liang@innolux.com" 
    send_to = [data['UserID']+"@innolux.com"]
    
    text = 'GBIM_ISSUEDATA_VS_SMARTFR.xlsx \n  筆數:'+str(data_count)
    subject = '檢核機制'
    files = []
    if data_count > 0 :
        files = [path_result+'GBIM_ISSUEDATA_VS_SMARTFR.xlsx']
    send_mail(send_from, send_to, subject, text, files)
    return data

@app.route('/gbim/sendFile_recommend', methods=['GET','POST'])
@login_required
def sendFile_recommend():
    data = {}
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    whereStr = 'where '
    whereDict = {}
    CREATE_YM = request.args.get("CREATE_YM")
    if CREATE_YM != '':
        whereStr = whereStr + ' a.CREATE_YM=:CREATE_YM'
        whereDict['CREATE_YM'] = CREATE_YM
    product_id = request.args.get('product_id' )
    if product_id != '':
        whereStr = whereStr + ' and a.product_id=:product_id'
        whereDict['product_id'] = product_id
    rc_id = request.args.get('rc_id' )
    if rc_id != '':
        whereStr = whereStr + ' and a.rc_id=:rc_id'
        whereDict['rc_id'] = rc_id
    data['CREATE_YM'] = CREATE_YM;
    data['product_id'] = product_id
    data['rc_id'] = rc_id
    path_result = r'/home/docker/gbimMVC/sendFile/'
    data['UserID'] = session['UserID']
    cur.execute('select a.CREATE_YM as "資料月份",a.rc_id as "RC ID",a.product_id as "PRODUCT ID",round(a.PREDICT_VALUE,0) as "全球備品庫存預估量(4個月)",round(b.fillnum,0) as "維修中心庫存預估量(1個月)",NVL(c.qty,0) as "維修中心庫存量" from (select rc_id,product_id,sum(PREDICT_VALUE) PREDICT_VALUE,CREATE_YM from ID_ADM.GBIM_PREDICT_RC_INVENTORY group by rc_id,product_id,CREATE_YM) a left join (select rc_id,product_id,sum(fillnum) fillnum from  ID_ADM.GBIM_PREDICT_RC_SHORTAGE group by rc_id,product_id) b on a.rc_id = b.rc_id and a.product_id=b.product_id left join (select rc_id,product_id,sum(qty) qty from RQ_ADM.GBIM_RC_INV_DAILY group by rc_id,product_id) c on a.rc_id = c.rc_id and a.product_id=c.product_id '+whereStr+' and a.rc_id in (\'A\' || chr(38) ||\'D-US\',\'ACCU\',\'Avatek\',\'COSMO\',\'EASCON\',\'GOC\',\'HL2\',\'HL3\',\'HLM\',\'JLM\',\'NDM\',\'NJJ\',\'NLM\',\'PCZ\',\'SEK\',\'SMM\',\'TGO\',\'TLM\',\'UPLUS\',\'ZZHC\',\'IGS\') and not (round(a.PREDICT_VALUE,0)=0 and round(b.fillnum,0)=0 and NVL(c.qty,0)=0) order by a.rc_id,a.product_id', whereDict)
    columns = [desc[0] for desc in cur.description]
    result = cur.fetchall()
    GBIM_PREDICT_RC_INVENTORY = pd.DataFrame(list(result), columns=columns)
    GBIM_PREDICT_RC_INVENTORY.to_excel(path_result+'GBIM_PREDICT_RC_INVENTORY.xlsx', index=False, encoding='utf-8-sig')
    data_count = len(GBIM_PREDICT_RC_INVENTORY.index)
    data['size'] = data_count
    
    send_from = "jacob.liang@innolux.com" 
    send_to = [data['UserID']+"@innolux.com"]
    
    text = 'GBIM_PREDICT_RC_INVENTORY.xlsx \n查詢條件:\n 1.CREATE_YM:'+CREATE_YM+'\n 2.product_id:'+product_id+'\n 3.rc_id:'+rc_id +'\n 筆數:'+str(data_count)
    subject = '全球備品庫存推薦'
    files = []
    if data_count > 0 :
        files = [path_result+'GBIM_PREDICT_RC_INVENTORY.xlsx']

    send_mail(send_from, send_to, subject, text, files)
    return data
@app.route('/gbim/sendFile_areaforecast', methods=['GET','POST'])
@login_required
def sendFile_areaforecast():
    data = {}
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    whereStr = 'where '
    whereDict = {} 
    CREATE_YM = request.args.get("CREATE_YM")
    if CREATE_YM != '':
        whereStr = whereStr + ' CREATE_YM=:CREATE_YM'
        whereDict['CREATE_YM'] = CREATE_YM
    customer = request.args.get("customer" )
    if customer != '':
        whereStr = whereStr + ' and customer=:customer'
        whereDict['customer'] = customer        
    failure_stage = request.args.get('failure_stage')
    if failure_stage != '':
        whereStr = whereStr + ' and failure_stage=:failure_stage'
        whereDict['failure_stage'] = failure_stage
    product_id = request.args.get('product_id' )
    if product_id != '':
        whereStr = whereStr + ' and product_id=:product_id'
        whereDict['product_id'] = product_id
    rc_id = request.args.get('rc_id' )
    if rc_id != '':
        whereStr = whereStr + ' and rc_id=:rc_id'
        whereDict['rc_id'] = rc_id  
    data['CREATE_YM'] = CREATE_YM;
    data['customer'] = customer
    data['failure_stage'] = failure_stage
    data['product_id'] = product_id
    data['rc_id'] = rc_id
    data['whereStr'] = whereStr
    path_result = r'/home/docker/gbimMVC/sendFile/'
    data['UserID'] = session['UserID']
    cur.execute('select create_ym as "資料月份",customer,failure_stage as "FAILURE STAGE",product_id as "PRODUCT ID",rc_id as "RC ID",qty from (select create_ym,customer,failure_stage,product_id,rc_id,round(sum(predict_qty*recent_data), 0) qty from ID_ADM.GBIM_PREDICT_RC_INVENTORY ' +whereStr+' and predict_qty*recent_data>0 GROUP BY create_ym,customer,failure_stage,rc_id,product_id) a where qty > 0',whereDict)
    columns = [desc[0] for desc in cur.description]
    result = cur.fetchall()
    GBIM_PREDICT_RC_RMA = pd.DataFrame(list(result), columns=columns)
    GBIM_PREDICT_RC_RMA.to_excel(path_result+'GBIM_PREDICT_RC_RMA.xlsx', index=False, encoding='utf-8-sig')
    data_count = len(GBIM_PREDICT_RC_RMA.index)
    data['size'] = data_count
    
    send_from = "jacob.liang@innolux.com" 
    send_to = [data['UserID']+"@innolux.com"]
    
    text = 'GBIM_PREDICT_RC_RMA.xlsx \n查詢條件:\n 1.CREATE_YM:'+CREATE_YM+'\n 2.customer:'+customer+'\n 3.failure_stage:'+failure_stage+'\n 4.product_id:'+product_id+'\n 5.rc_id:'+rc_id+'\n 筆數:'+str(data_count)
    subject = '全球不良品區域預測'
    files = []
    if data_count > 0 :
        files = [path_result+'GBIM_PREDICT_RC_RMA.xlsx']

    send_mail(send_from, send_to, subject, text, files)
    return data

@app.route('/gbim/sendFile_smartfr', methods=['GET','POST'])
@login_required
def sendFile_smartfr():
    data = {}
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    whereStr = 'where '
    whereDict = {}
    yyyymm = request.args.get("yyyymm")
    if yyyymm != '':
        whereStr = whereStr + 'yyyymm=:yyyymm'
        whereDict['yyyymm'] = yyyymm
    customer = request.args.get("customer" )
    if customer != '':
        whereStr = whereStr + ' and customer=:customer'
        whereDict['customer'] = customer    
    model_name = request.args.get('model_name')
    if model_name != '':
        whereStr = whereStr + ' and model_name=:model_name'
        whereDict['model_name'] = model_name
    product_id = request.args.get('product_id' )
    if product_id != '':
        whereStr = whereStr + ' and product_id=:product_id'
        whereDict['product_id'] = product_id
    status = request.args.get('status')
    if status != '':
        whereStr = whereStr + ' and status=:status'
        whereDict['status'] = status     
    data['yyyymm'] = yyyymm;
    data['customer'] = customer
    data['model_name'] = model_name
    data['product_id'] = product_id
    data['status'] = status
    data['whereStr'] = whereStr
    path_result = r'/home/docker/gbimMVC/sendFile/'
    data['UserID'] = session['UserID']
    cur.execute('select yyyymm as "Smart FR更新月份",customer,application,model_name as "MODEL NAME",product_id as "PRODUCT ID",predict_qty as "PREDICT QTY",warranty_fulfill as "是否為保固期備滿",status as "FAILURE STAGE",warranty_len as "保固期" \
                from RQ_ADM.GBIM_SMART_FR_PREDICT '+whereStr,whereDict)
    columns = [desc[0] for desc in cur.description] 
    result = cur.fetchall()
    GBIM_SMART_FR_PREDICT = pd.DataFrame(list(result), columns=columns)
    GBIM_SMART_FR_PREDICT.to_excel(path_result+'GBIM_SMART_FR_PREDICT.xlsx', index=False, encoding='utf-8-sig')
    data_count = len(GBIM_SMART_FR_PREDICT.index)
    data['size'] = data_count
    send_from = "jacob.liang@innolux.com" 
    send_to = [data['UserID']+"@innolux.com"]
    
    text = 'GBIM_SMART_FR_PREDICT.xlsx \n查詢條件:\n 1.yyyymm:'+yyyymm+'\n 2.customer:'+customer+'\n 3.model_name:'+model_name+'\n 4.product_id:'+product_id+'\n 5.status:'+status+'\n 筆數:'+str(data_count)
    #text = 'GBIM_SMART_FR_PREDICT.xlsx \n查詢條件:\n 1.yyyymm: \n 2.customer: \n 筆數:'+str(GBIM_SMART_FR_PREDICT.size)
    subject = 'SMART FR 決策輔助 '
    files = []
    if data_count > 0 :
        files = [path_result+'GBIM_SMART_FR_PREDICT.xlsx']
    send_mail(send_from, send_to, subject, text, files)
    return data
@app.route('/gbim/sendFile_safetystock', methods=['GET','POST'])
@login_required
def sendFile_safetystock():
    data = {}
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
    cur = con.cursor()
    whereStr = 'where 1=1'
    whereDict = {} 
    create_ym = request.args.get("create_ym")
    if create_ym != '' and create_ym != 'ALL':
        whereStr = whereStr + ' and create_ym=:create_ym'
        whereDict['create_ym'] = create_ym
    rc_id = request.args.get("rc_id" )
    if rc_id != '':
        whereStr = whereStr + ' and rc_id=:rc_id'
        whereDict['rc_id'] = rc_id    
    part_name = request.args.get('part_name')
    if part_name != '':
        whereStr = whereStr + ' and part_name=:part_name'
        whereDict['part_name'] = part_name
    plant = request.args.get('plant' )
    if plant != '':
        whereStr = whereStr + ' and plant=:plant'
        whereDict['plant'] = plant
        
    data['create_ym'] = create_ym;
    data['rc_id'] = rc_id
    data['part_name'] = part_name
    data['plant'] = plant 
    data['whereStr'] = whereStr
    path_result = r'/home/docker/gbimMVC/sendFile/'
    data['UserID'] = session['UserID']
    cur.execute(' select a.create_ym as "年月",a.rc_id as "RC_ID",a.part_name as "PART_NAME",a.product_id as "PRODUCT ID",a.transfer_qty as "調撥數量",NVL(a.plant,\'NA\') as "Plant",NVL(a.part_no,\'NA\') as "需提貨料號",a.adjust_forecast as "Adjust Forecast" ,NVL(b.adjust_forecast, -1) as "Adjust Forecast(上個月)" from ID_ADM.GPIM_PART_FORECAST a left join (select rc_id,product_id ,part_name,part_no,adjust_forecast,create_ym from ID_ADM.GPIM_PART_FORECAST) b on a.rc_id=b.rc_id and a.product_id=b.product_id and a.part_name=b.part_name  and a.part_no=b.part_no and b.create_ym=TO_CHAR( add_months(trunc(TO_DATE(a.create_ym, \'YYYY-MM\'),\'mm\'),-1), \'YYYY-MM\') where a.create_ym > \'2021-12\' order by a.create_ym desc '+whereStr,whereDict)
    columns = [desc[0] for desc in cur.description] 
    result = cur.fetchall()
    GPIM_PART_FORECAST = pd.DataFrame(list(result), columns=columns)
    GPIM_PART_FORECAST.to_excel(path_result+'GPIM_PART_FORECAST.xlsx', index=False, encoding='utf-8-sig')
    data_count = len(GPIM_PART_FORECAST.index)
    data['size'] = data_count
    send_from = "jacob.liang@innolux.com" 
    send_to = [data['UserID']+"@innolux.com"]
    
    text = 'GPIM_PART_FORECAST.xlsx \n查詢條件:\n 1.yyyymm:'+yyyymm+'\n 2.customer:'+customer+'\n 3.model_name:'+model_name+'\n 4.product_id:'+product_id+'\n 5.status:'+status+'\n 筆數:'+str(data_count) 
    subject = 'SMART FR 決策輔助 '
    files = []
    if data_count > 0 :
        files = [path_result+'GPIM_PART_FORECAST.xlsx']
    send_mail(send_from, send_to, subject, text, files)
    return data
def send_mail(send_from, send_to, subject, text, files=None, server="10.53.248.103", port = 25):
    assert isinstance(send_to, list)
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)
    smtp = smtplib.SMTP(server, port)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()
@app.route('/gbim/download', methods=['GET','POST'])
@login_required
def download():    
    filename = request.form['filename']
    path_result = r'/home/docker/gbimMVC/sendFile'
    if filename == 'VIZIO_FCST_OUTPUT_2.xlsx' : # set_material
        con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
        cur = con.cursor()
        whereStr = ' where 1=1 '
        whereDict = {} 
        FCST_MONTH = request.form["FCST_MONTH"]
        if FCST_MONTH != '' :
            whereStr = whereStr + ' and TO_CHAR(FCST_MONTH, \'YYYY/MM\')=:FCST_MONTH'
            whereDict['FCST_MONTH'] = FCST_MONTH 
        material_item_string = request.form["material_item_list"] 
        if material_item_string != '' : 
            whereStr = whereStr + " and material_item in ("+material_item_string+")" 
        # GROUPCODE,MATERIAL_ITEM,FCST_QTY,INVENTORY,ON_WAY_QTY,ALERT_INVENTORY,TRANSFER_QTY,VIZIO_MODEL
        cur.execute('select TO_CHAR(FCST_MONTH, \'YYYY/MM\') as "預估月份 (N)",GROUPCODE,MATERIAL_ITEM as "Material Item",FCST_QTY as "N+3 個月預估需求量",INVENTORY as "RC 庫存量",ON_WAY_QTY as "On Way Qty",ALERT_INVENTORY as "警戒水位",TRANSFER_QTY as "調撥數量",VIZIO_MODEL as "VIZIO MODEL" from RQ_ADM.VIZIO_FCST_OUTPUT_2 '+whereStr+' order by MATERIAL_ITEM desc ',whereDict)
    if filename == 'VIZIO_FCST_OUTPUT.xlsx' : # set_forecast
        con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
        cur = con.cursor()
        whereStr = ' where 1=1 '
        whereDict = {} 
        FCST_MONTH = request.form["FCST_MONTH"]
        if FCST_MONTH != '' :
            whereStr = whereStr + ' and TO_CHAR(FCST_MONTH, \'YYYY/MM\')=:FCST_MONTH'
            whereDict['FCST_MONTH'] = FCST_MONTH
        MOTHER_MODEL_NAME = request.form["MOTHER_MODEL_NAME"]
        if MOTHER_MODEL_NAME != '' :
            whereStr = whereStr + ' and MOTHER_MODEL_NAME=:MOTHER_MODEL_NAME'
            whereDict['MOTHER_MODEL_NAME'] = MOTHER_MODEL_NAME
        PHASE = request.form["PHASE"]
        if PHASE != '' :
            whereStr = whereStr + ' and PHASE=:PHASE'
            whereDict['PHASE'] = PHASE
        cur.execute('select TO_CHAR(FCST_MONTH, \'YYYY/MM\') as "預估月份 (N)",MOTHER_MODEL_NAME as "機種 (Grouping)",MODEL_NAME as "機種",PHASE as "產品週期",FCST_QTY_A as "N+3 個月預估需求量",INVENTORY_A as "RC 庫存量 (A)",ON_WAY_QTY as "On Way Qty",RG_QTY as "RG Qty",ALERT_INVENTORY as "警戒水位",TRANSFER_QTY_A as "調撥數量 (A)",FCST_QTY_B as "N+1 個月預估需求量",INVENTORY_B as "RC 庫存量 (B)",TRANSFER_QTY_B as "調撥數量 (B)" from RQ_ADM.VIZIO_FCST_OUTPUT '+whereStr+' order by FCST_MONTH desc ',whereDict) 
    elif filename == 'VIZIO_FCST_OUTPUT_CHECKUP.xlsx' : # set_audit
        con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
        cur = con.cursor()
        whereStr = ' where 1=1 '
        whereDict = {} 
        FCST_MONTH = request.form["FCST_MONTH"]
        if FCST_MONTH != '' :
            whereStr = whereStr + ' and TO_CHAR(FCST_MONTH, \'YYYY/MM\')=:FCST_MONTH'
            whereDict['FCST_MONTH'] = FCST_MONTH
        MOTHER_MODEL_NAME = request.form["MOTHER_MODEL_NAME"]
        if MOTHER_MODEL_NAME != '' :
            whereStr = whereStr + ' and MOTHER_MODEL_NAME=:MOTHER_MODEL_NAME'
            whereDict['MOTHER_MODEL_NAME'] = MOTHER_MODEL_NAME
        PHASE = request.form["PHASE"]
        if PHASE != '' :
            whereStr = whereStr + ' and PHASE=:PHASE'
            whereDict['PHASE'] = PHASE
        cur.execute('select TO_CHAR(FCST_MONTH, \'YYYY/MM\') as "預估月份 (N)",MOTHER_MODEL_NAME as "機種 (Grouping)",MODEL_NAME as "機種",PHASE as "產品週期",TRANSFER_N4 as "(N-4) 個月前的調撥量",COMSUMPTION_N4_A as "(N-4) 個月前的耗用量 (A)",COMSUMPTION_A as "本月累積耗用量 (A)",COMSUMPTION_AVG_A as "平均月耗用 (A)",TRANSFER_N2 as "(N-2) 個月前的調撥量",COMSUMPTION_N2_B as "(N-2) 個月前的耗用量 (B)",COMSUMPTION_B as "本月累積耗用量 (B)",COMSUMPTION_AVG_B as "平均月耗用 (B)" from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP '+whereStr+' order by FCST_MONTH desc ',whereDict)
    elif filename == 'GPIM_PART_FORECAST.xlsx' : # safetystock
        con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", )
        cur = con.cursor()
        whereStr = ' where 1=1 '
        whereDict = {} 
        create_ym = request.form["create_ym"]
        if create_ym != '' and create_ym != 'ALL':
            whereStr = whereStr + ' and a.create_ym=:create_ym'
            whereDict['create_ym'] = create_ym
        else :
            whereStr = whereStr + ' and a.create_ym > \'2021-12\''
        rc_id = request.form["rc_id"]
        if rc_id != '':
            whereStr = whereStr + ' and a.rc_id=:rc_id'
            whereDict['rc_id'] = rc_id    
        part_name = request.form['part_name']
        if part_name != '':
            whereStr = whereStr + ' and a.part_name=:part_name'
            whereDict['part_name'] = part_name
        plant = request.form['plant']
        if plant != '':
            whereStr = whereStr + ' and a.plant=:plant'
            whereDict['plant'] = plant 
        cur.execute('select a.create_ym as "年月",a.rc_id as "RC_ID",a.part_name as "PART_NAME",a.product_id as "PRODUCT ID",a.transfer_qty as "調撥數量",NVL(a.plant,\'NA\') as "Plant",NVL(a.part_no,\'NA\') as "需提貨料號",a.adjust_forecast as "Adjust Forecast" ,NVL(b.adjust_forecast, -1) as "Adjust Forecast(上個月)" from ID_ADM.GPIM_PART_FORECAST a left join (select rc_id,product_id ,part_name,part_no,adjust_forecast,create_ym from ID_ADM.GPIM_PART_FORECAST) b on a.rc_id=b.rc_id and a.product_id=b.product_id and a.part_name=b.part_name  and a.part_no=b.part_no and b.create_ym=TO_CHAR( add_months(trunc(TO_DATE(a.create_ym, \'YYYY-MM\'),\'mm\'),-1), \'YYYY-MM\') '+whereStr+' order by a.create_ym desc ',whereDict)        
    elif filename == 'TBU_RQM_PARTS_DAILY_AGING.xlsx' : # alarm
        con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", ) 
        cur = con.cursor()
        cur.execute("select distinct PART_NO from id_adm.GPIM_INSTEAD_PART_NO where create_ym=(select max(create_ym) from id_adm.GPIM_INSTEAD_PART_NO)")
        PART_NO_list = ",".join( ["'"+e[0]+"'" for e in list(cur.fetchall())])
        cur.close()
        con.close()
        con = cx_Oracle.connect(dbconfig.rmarptDB, encoding="UTF-8", nencoding="UTF-8", )
        cur = con.cursor()
        whereStr = ' '
        whereDict = {} 
        mg_name_m = request.form['mg_name_m']
        if mg_name_m != '' :
            whereStr = whereStr + ' and mg_name_m=:mg_name_m'
            whereDict['mg_name_m'] = mg_name_m
        rc_id = request.form['rc_id']
        if rc_id != '':
            whereStr = whereStr + ' and rc_id=:rc_id'
            whereDict['rc_id'] = rc_id    
        cur.execute('select rc_id as "RC_ID",mg_name_m as "PART_NAME",part_no as "PART NUMBER",sum(qty) as "報廢數量",NVL(round(sum(TOTAL_PRICE_TWD),0),-1) as "報廢金額NTD" from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = \'Key\' and aging>240 and stk_location in (\'Stock\',\'In-Line\') and rc_id in (\'ACCU\',\'EASCON\',\'ZZHC\',\'TGO\',\'SMM\',\'UPLUS\',\'IGS\') and part_no not in ('+PART_NO_list+') and TOTAL_PRICE_TWD is not NULL '+whereStr+' GROUP by rc_id,mg_name_m,part_no',whereDict)
    elif filename == 'VIZIO_FTP_RAW_DATA.xlsx' : # ftp raw data
        con = cx_Oracle.connect(dbconfig.rmarptDB, encoding="UTF-8", nencoding="UTF-8", ) 
        cur = con.cursor()
        whereStr = ' where 1=1 '
        whereDict = {} 
        startDate = request.form["startDate"]
        endDate = request.form["endDate"]
        print('startDate:',startDate,',endDate:',endDate) 
        cur.execute('select asp,sr_number,TO_CHAR(date_create, \'YYYY/MM/DD\') date_create,sr_type,p_model,p_serialnumber,TO_CHAR(purchasedate, \'YYYY/MM/DD\') purchasedate,TO_CHAR(send_date, \'YYYY/MM/DD\') send_date,material_item,\'Z_VIZIO_ACC_SERVICE_RPT\' rpt,rpt_file_name from RMA_ADMIN.Z_VIZIO_ACC_SERVICE_RPT where TO_CHAR(send_date, \'YYYY/MM/DD\') between :startDate and :endDate union all select providerid as asp,osr as sr_number,TO_CHAR(date_issued, \'YYYY/MM/DD\') date_create,sr_type,tv_model p_model,tv_serialno p_serialnumber,TO_CHAR(purchasedate, \'YYYY/MM/DD\') purchasedate,TO_CHAR(ship_date, \'YYYY/MM/DD\') send_date, material_item,\'Z_VIZIO_OSR_PART_SHIPPED_RPT\' rpt,rpt_file_name from RMA_ADMIN.Z_VIZIO_OSR_PART_SHIPPED_RPT where TO_CHAR(date_issued, \'YYYY/MM/DD\') between :startDate and :endDate union all select asp,sr_number,TO_CHAR(date_create, \'YYYY/MM/DD\') date_create,sr_type,p_model,p_serialnumber,TO_CHAR(purchasedate, \'YYYY/MM/DD\') purchasedate,TO_CHAR(send_date, \'YYYY/MM/DD\') send_date,material_item,\'Z_VIZIO_AR_SR_RR_OSS_RPT\' rpt,rpt_file_name from RMA_ADMIN.Z_VIZIO_AR_SR_RR_OSS_RPT where TO_CHAR(send_date, \'YYYY/MM/DD\') between :startDate and :endDate union all select asp,sr_number,TO_CHAR(date_create, \'YYYY/MM/DD\') date_create,sr_type,p_model,p_serialnumber,TO_CHAR(purchasedate, \'YYYY/MM/DD\') purchasedate,TO_CHAR(daterepair, \'YYYY/MM/DD\') send_date,material_item,\'Z_VIZIO_WEEKLY_REPAIR_RPT\' rpt,rpt_file_name from RMA_ADMIN.Z_VIZIO_WEEKLY_REPAIR_RPT where TO_CHAR(daterepair, \'YYYY/MM/DD\') between :startDate and :endDate order by rpt , date_create desc',{'startDate':startDate,'endDate':endDate})
        columns = [desc[0] for desc in cur.description] 
        result = cur.fetchall()
        excelFile1 = pd.DataFrame(list(result), columns=columns)
        
        cur.execute('select model_number,serial_number,grade,TO_CHAR(date_in, \'YYYY/MM/DD\') date_in,TO_CHAR(date_out, \'YYYY/MM/DD\') date_out,rpt_file_name from RMA_ADMIN.Z_VIZIO_DAILY_ACTIV_BUFFER_RPT where TO_CHAR(date_in, \'YYYY/MM/DD\') between :startDate and :endDate order by date_in desc',{'startDate':startDate,'endDate':endDate})
        columns = [desc[0] for desc in cur.description] 
        result = cur.fetchall()
        excelFile2 = pd.DataFrame(list(result), columns=columns)
        
        cur.execute('select PART_NO,TTL_AVL_QTY,MATERIAL_ITEM,GROUPCODE,KEY_PART,RPT_FILE_NAME from RMA_ADMIN.Z_VIZIO_SPARE_PARTS_RPT order by PART_NO')
        columns = [desc[0] for desc in cur.description] 
        result = cur.fetchall()
        excelFile3 = pd.DataFrame(list(result), columns=columns)
        
        with pd.ExcelWriter(path_result+'/'+filename) as writer:  
            excelFile3.to_excel(writer, index=False, encoding='utf-8-sig', sheet_name='spare')
            excelFile2.to_excel(writer, index=False, encoding='utf-8-sig', sheet_name='daily rpt')
            excelFile1.to_excel(writer, index=False, encoding='utf-8-sig', sheet_name='4 rpt')
        return send_from_directory(path_result, filename, as_attachment=True)
    columns = [desc[0] for desc in cur.description] 
    result = cur.fetchall()
    excelFile = pd.DataFrame(list(result), columns=columns)
    excelFile.to_excel(path_result+'/'+filename, index=False, encoding='utf-8-sig')
    return send_from_directory(path_result, filename, as_attachment=True)
@app.route('/gbim/smartfr', methods=['GET','POST'])
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
    data['UserID'] = session['UserID']
    smart_fr_predict = {} # OrderedDict();
    #cur.execute("select STATUS,YYYYMM,sum(PREDICT_QTY) from RQ_ADM.GBIM_SMART_FR_PREDICT group by STATUS,YYYYMM order by YYYYMM,STATUS") 
    #cur.execute("select YYYYMM, max(decode(STATUS,'FR',pp)) FR,max(decode(STATUS,'LR',pp)) LR from (select STATUS,YYYYMM,sum(PREDICT_QTY) pp from RQ_ADM.GBIM_SMART_FR_PREDICT group by STATUS,YYYYMM) a group by YYYYMM")
    cur.execute("select YYYYMM, max(decode(WF,'FR-MP',PQ)), max(decode(WF,'FR-EOL',PQ)) ,max(decode(WF,'LR-MP',PQ)),max(decode(WF,'LR-EOL',PQ)) from ( \
                 select STATUS ||'-'||CASE WHEN warranty_fulfill='N' THEN 'MP' ELSE 'EOL' END as wf ,YYYYMM,sum(PREDICT_QTY) pq from RQ_ADM.GBIM_SMART_FR_PREDICT where YYYYMM>202110 group by STATUS,warranty_fulfill,YYYYMM \
                 ) a group by YYYYMM order by YYYYMM")	
    c = 0
    ym_list = []
    for r in cur :
        tmp = {} #OrderedDict() 
        tmp['YYYYMM'] = r[0]
        tmp['FR-MP'] = r[1]
        tmp['FR-EOL'] = r[2] 
        tmp['LR-MP'] = r[3]
        tmp['LR-EOL'] = r[4]
        smart_fr_predict[c] = tmp
        ym_list.append(r[0])
        c=c+1
    data['smart_fr_predict'] = smart_fr_predict
    data['ym_list'] = ym_list
    smart_fr_application = {}
    cur.execute("select STATUS, NVL(max(decode(application,'AA-BD4',PQ)),0), NVL(max(decode(application,'AUTO-BD5',PQ)),0), NVL(max(decode(application,'CE',PQ)),0),\
                 NVL(max(decode(application,'IAVM',PQ)),0), NVL(max(decode(application,'MONITOR',PQ)),0), NVL(max(decode(application,'MP',PQ)),0), \
				 NVL(max(decode(application,'NB',PQ)),0),NVL(max(decode(application,'SET_TV',PQ)),0), NVL(max(decode(application,'TABLET',PQ)),0),\
				 NVL(max(decode(application,'TV',PQ)),0) from (\
                 select STATUS,application,sum(PREDICT_QTY) PQ from RQ_ADM.GBIM_SMART_FR_PREDICT where YYYYMM>202110 GROUP by STATUS,application order by STATUS,application\
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
    smart_fr_list = {}	

    if request.method == 'POST':
        yyyymm = request.form['yyyymm']
    else :
        cur.execute("select max(yyyymm) from RQ_ADM.GBIM_SMART_FR_PREDICT")
        yyyymm = cur.fetchone()[0]
    data['yyyymm'] = yyyymm	
    #print(yyyymm) 
    
    #cur.execute("select customer,application,model_name,product_id,predict_qty,warranty_fulfill,status,warranty_len,yyyymm from RQ_ADM.GBIM_SMART_FR_PREDICT order by yyyymm fetch first 35 rows only")
    cur.execute("select customer,application,model_name,product_id,predict_qty,warranty_fulfill,status,warranty_len,yyyymm from RQ_ADM.GBIM_SMART_FR_PREDICT where yyyymm = :yyyymm order by yyyymm",{'yyyymm':yyyymm})
    c = 0
    for r in cur :
        tmp = {}
        tmp['customer'] = r[0]
        tmp['application'] = r[1]
        tmp['model_name'] = r[2] 
        tmp['product_id'] = r[3]
        tmp['predict_qty'] = r[4]
        tmp['warranty_fulfill'] = r[5]
        tmp['status'] = r[6]
        tmp['warranty_len'] = r[7]
        tmp['yyyymm'] = r[8]
        smart_fr_list[c] = tmp
        c=c+1
    data['smart_fr_list'] = smart_fr_list
    
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
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    if request.method == 'POST':
        CREATE_YM = request.form['CREATE_YM']
    else :
        cur.execute("select max(CREATE_YM) from id_adm.GBIM_PREDICT_RC_INVENTORY")
        CREATE_YM = cur.fetchone()[0]
    predict_rc_inventory = {}
    inventory_list = ['A&D-US','ACCU','Avatek','COSMO','EASCON','GOC','HL2','HL3','HLM','JLM','NDM','NJJ','NLM','PCZ','SEK','SMM','TGO','TLM','UPLUS','ZZHC','IGS']
    ym_list = []
    cur.execute("select rc_id,status,CREATE_YM,sum(recent_data*predict_qty) from id_adm.GBIM_PREDICT_RC_INVENTORY where rc_id in ('A' || chr(38) || 'D-US','ACCU','Avatek','COSMO','EASCON','GOC','HL2','HL3','HLM','JLM','NDM','NJJ','NLM','PCZ','SEK','SMM','TGO','TLM','UPLUS','ZZHC','IGS') and CREATE_YM=:CREATE_YM group by rc_id,status,CREATE_YM order by CREATE_YM,status,rc_id",{'CREATE_YM':CREATE_YM})
    
    c = 0
    tmp = {}
    for r in cur :        
        rc_id = r[0]
        status = r[1]
        ym = r[2] 
        qty = r[3] 
        #predict_rc_inventory[rc_id+'-'+status] = qty
        tmp[rc_id+'-'+status] = qty
        if c == 0 :
            ym_list.append(ym)
        if (ym not in ym_list) and c > 0 :
            predict_rc_inventory[ym] = tmp
            ym_list.append(ym)
            tmp = {}        
        c = c + 1 
    predict_rc_inventory[ym] = tmp 
    data['inventory_list'] = inventory_list
    data['predict_rc_inventory'] = predict_rc_inventory
    data['ym_list'] = ym_list
    
    cur.execute("select * from (select customer,failure_stage,product_id,rc_id,round(sum(predict_qty*recent_data), 0) qty from ID_ADM.GBIM_PREDICT_RC_INVENTORY where create_ym=:CREATE_YM and predict_qty*recent_data>0 GROUP BY create_ym,customer,failure_stage,rc_id,product_id) a where qty > 0",{'CREATE_YM':CREATE_YM})
    predict_rc_inventory_list = {}
    c = 0
    for r in cur :
        tmp = {}
        tmp['customer'] = r[0]
        tmp['failure_stage'] = r[1]
        tmp['product_id'] = r[2] 
        tmp['rc_id'] = r[3]
        tmp['qty'] = r[4]
        predict_rc_inventory_list[str(c)] = tmp
        c=c+1
    data['predict_rc_inventory_list'] = predict_rc_inventory_list
    data['CREATE_YM'] = CREATE_YM

    cur.close()
    con.close()	
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
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    cur.execute("select UNIQUE CREATE_YM from ID_ADM.GBIM_PREDICT_RC_INVENTORY")
    ym_list = []
    for r in cur:
        ym_list.append(r[0])
    data['ym_list'] = ym_list
    if request.method == 'POST':
        CREATE_YM = request.form['CREATE_YM']
    else :
        cur.execute("select max(CREATE_YM) from id_adm.GBIM_PREDICT_RC_INVENTORY")
        CREATE_YM = cur.fetchone()[0]
    data['CREATE_YM'] = CREATE_YM
    cur.execute("select a.rc_id,a.PREDICT_VALUE,b.fillnum,NVL(c.qty,0) from (select rc_id,sum(PREDICT_VALUE) PREDICT_VALUE,CREATE_YM from ID_ADM.GBIM_PREDICT_RC_INVENTORY group by rc_id,CREATE_YM) a left join (select rc_id,sum(fillnum) fillnum from  ID_ADM.GBIM_PREDICT_RC_SHORTAGE group by rc_id) b on a.rc_id = b.rc_id left join (select rc_id,sum(qty) qty from RQ_ADM.GBIM_RC_INV_DAILY group by rc_id) c on a.rc_id = c.rc_id where a.rc_id in ('A' || chr(38) ||'D-US','ACCU','Avatek','COSMO','EASCON','GOC','HL2','HL3','HLM','JLM','NDM','NJJ','NLM','PCZ','SEK','SMM','TGO','TLM','UPLUS','ZZHC','IGS') and a.CREATE_YM=:CREATE_YM order by rc_id",{'CREATE_YM':CREATE_YM})
    
    rc_id_data = []
    PREDICT_VALUE_data = []
    fillnum_data = []
    qty_data = []
    for r in cur :
        rc_id_data.append(r[0])
        PREDICT_VALUE_data.append(r[1])
        fillnum_data.append(r[2])
        qty_data.append(r[3])
    data['rc_id_data'] = rc_id_data
    data['PREDICT_VALUE_data'] = PREDICT_VALUE_data
    data['fillnum_data'] = fillnum_data
    data['qty_data'] = qty_data

    cur.execute("select a.rc_id,a.product_id,round(a.PREDICT_VALUE,0),round(b.fillnum,0),NVL(c.qty,0) from (select rc_id,product_id,sum(PREDICT_VALUE) PREDICT_VALUE,CREATE_YM from ID_ADM.GBIM_PREDICT_RC_INVENTORY group by rc_id,product_id,CREATE_YM) a left join (select rc_id,product_id,sum(fillnum) fillnum from  ID_ADM.GBIM_PREDICT_RC_SHORTAGE group by rc_id,product_id) b on a.rc_id = b.rc_id and a.product_id=b.product_id left join (select rc_id,product_id,sum(qty) qty from RQ_ADM.GBIM_RC_INV_DAILY group by rc_id,product_id) c on a.rc_id = c.rc_id and a.product_id=c.product_id where a.rc_id in ('A' || chr(38) ||'D-US','ACCU','Avatek','COSMO','EASCON','GOC','HL2','HL3','HLM','JLM','NDM','NJJ','NLM','PCZ','SEK','SMM','TGO','TLM','UPLUS','ZZHC','IGS') and a.CREATE_YM=:CREATE_YM and not (round(a.PREDICT_VALUE,0)=0 and round(b.fillnum,0)=0 and NVL(c.qty,0)=0) order by rc_id,product_id",{'CREATE_YM':CREATE_YM})
    predict_rc_inventory_list = {}
    c = 0
    for r in cur :
        tmp = {}
        tmp['rc_id'] = r[0]
        tmp['product_id'] = r[1]
        tmp['predict_value'] = r[2] 
        tmp['fillnum'] = r[3]
        tmp['qty'] = r[4]
        predict_rc_inventory_list[str(c)] = tmp
        c=c+1
    data['predict_rc_inventory_list'] = predict_rc_inventory_list
    cur.close()
    con.close()
    return render_template('recommend.html', data = data)

@app.route('/gbim/alarm', methods=['GET'])
@login_required
def alarm():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"呆滯物料預警"
    }
    data['userChineseName'] = session['userChineseName']
    data['UserID'] = session['UserID']
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", ) 
    cur = con.cursor()
    cur.execute("select distinct PART_NO from id_adm.GPIM_INSTEAD_PART_NO where create_ym=(select max(create_ym) from id_adm.GPIM_INSTEAD_PART_NO)")
    PART_NO_list = ",".join( ["'"+e[0]+"'" for e in list(cur.fetchall())])
    cur.close()
    con.close()
    part_name_list = []
    total_price_twd_list = []
    PART_NO_PRICE_list = {}
    series = []
    con = cx_Oracle.connect(dbconfig.rmarptDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor() 
    #cur.execute("select MG_NAME_M,rc_id,round(sum(TOTAL_PRICE_TWD),2) from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = 'Key' and aging>240 and stk_location in ('Stock','In-Line') and rc_id in ('ACCU','EASCON','ZZHC','TGO','SMM','UPLUS','IGS') and part_no not in ("+PART_NO_list+") group by MG_NAME_M")
    cur.execute("select aa.rc_id,aa.MG_NAME_M,NVL(c.TOTAL_PRICE_TWD,0) from (select rc_id,MG_NAME_M from (select distinct rc_id from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = 'Key' and aging>240 and stk_location in ('Stock','In-Line') and rc_id in ('ACCU','EASCON','ZZHC','TGO','SMM','UPLUS','IGS') and part_no not in ("+PART_NO_list+") ) a,(select distinct MG_NAME_M from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = 'Key' and aging>240 and stk_location in ('Stock','In-Line') and rc_id in ('ACCU','EASCON','ZZHC','TGO','SMM','UPLUS','IGS') and part_no not in ("+PART_NO_list+") ) b ) aa left join (select  rc_id,MG_NAME_M,round(sum(TOTAL_PRICE_TWD),0) TOTAL_PRICE_TWD from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = 'Key' and aging>240 and stk_location in ('Stock','In-Line') and rc_id in ('ACCU','EASCON','ZZHC','TGO','SMM','UPLUS','IGS') and part_no not in ("+PART_NO_list+") group by MG_NAME_M,rc_id) c on aa.rc_id = c.rc_id and aa.MG_NAME_M = c.MG_NAME_M ")
    c = 0
    rc_id = ''
    tmp = {'data': []}
    TOTAL_PRICE_TWD_total = 0
    for r in cur :        
        if rc_id != '' and rc_id != r[0] :
            tmp['name'] = rc_id
            tmp['type'] = 'bar'
            tmp['stack'] = 'total'
            tmp['label'] = {'show': 'true'}
            #tmp['emphasis'] = {'focus': 'series'}
            series.append(tmp);
            tmp = {'data': []}
        rc_id = r[0]
        MG_NAME_M = r[1]
        TOTAL_PRICE_TWD = r[2]
        if TOTAL_PRICE_TWD > 1000 :
            TOTAL_PRICE_TWD_total = TOTAL_PRICE_TWD_total + TOTAL_PRICE_TWD
            tmp['data'].append(TOTAL_PRICE_TWD);
            if MG_NAME_M not in part_name_list :
                part_name_list.append(MG_NAME_M);
        else :
            tmp['data'].append(0);
        #total_price_twd_list.append(r[1]);
    tmp['name'] = rc_id
    tmp['type'] = 'bar'
    tmp['stack'] = 'total'
    tmp['label'] = {'show': 'true'}#{ 'normal': "{ show: true, position: 'top', formatter: (params) => { let total = 0; this.mySeries.forEach(serie => { total += serie.data[params.dataIndex]; }) return total; } }" }
    #tmp['emphasis'] = {'focus': 'series'}
    series.append(tmp);
    data['part_name_list'] = part_name_list
    data['series'] = series
    data['TOTAL_PRICE_TWD_total'] = format(TOTAL_PRICE_TWD_total,',')
    aging_list = {}
    cur.execute("select rc_id,mg_name_m,part_no,sum(qty),NVL(round(sum(TOTAL_PRICE_TWD),0),-1) from RMA_AP.TBU_RQM_PARTS_DAILY_AGING_V WHERE mg_name_l = 'Key' and aging>240 and stk_location in ('Stock','In-Line') and rc_id in ('ACCU','EASCON','ZZHC','TGO','SMM','UPLUS','IGS') and part_no not in ("+PART_NO_list+") and TOTAL_PRICE_TWD is not NULL GROUP by rc_id,mg_name_m,part_no")
    c = 0
    for r in cur :
        tmp = {}
        tmp['rc_id'] = r[0]
        tmp['mg_name_m'] = r[1]
        tmp['part_no'] = r[2]
        tmp['qty'] = r[3]
        #tmp['total_price_twd'] = 'NA' if r[4] == -1 else format(r[4],',')
        tmp['total_price_twd'] = format(r[4],',')#r[4]
        aging_list[str(c)] = tmp
        c = c + 1
    data['aging_list'] = aging_list
    cur.close()
    con.close()
    return render_template('alarm.html', data = data)

@app.route('/gbim/safetystock', methods=['GET'])
@login_required
def safetystock():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"維修缺料分析"
    }
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8", ) 
    cur = con.cursor()
    data['userChineseName'] = session['userChineseName']
    data['UserID'] = session['UserID']
    if request.method == 'POST':
        CREATE_YM = request.form['CREATE_YM']
    else :
        cur.execute("select max(create_ym) from ID_ADM.GPIM_PART_FORECAST")
        CREATE_YM = cur.fetchone()[0]
    
    cur.execute("select distinct create_ym from ID_ADM.GPIM_PART_FORECAST where create_ym>'2021-12' order by create_ym desc")
    ym_list = []
    for r in cur:
        ym_list.append(r[0])
    data['ym_list'] = ym_list
    #data['part_name_list'] = []
    rc_id_list = []
    forecast_list = {}
    cur.execute("select part_name,rc_id,af,hq from ( select rc_id,part_name,sum(adjust_forecast) af,sum(on_hand_qty)+sum(DELIVERY_QTY)+sum(ON_WAY_QTY) hq from ID_ADM.GPIM_PART_FORECAST where create_ym=(select max(create_ym) from ID_ADM.GPIM_PART_FORECAST) group by rc_id,part_name ) where af>20 order by part_name,rc_id")
    c = 0
    tmp = {}
    part_name = ''
    for r in cur :        
        if c > 0 and part_name != r[0] :
            forecast_list[part_name] = tmp
            tmp = {}
        part_name = r[0]
        rc_id = r[1]
        #tmp.append({'rc_id':r[1], 'af':r[2], 'hq':r[3]})
        tmp[r[1]] = {'af':r[2], 'hq':r[3]}
        if rc_id not in rc_id_list:
            rc_id_list.append(rc_id)
        c = c + 1
    forecast_list[part_name] = tmp
    """
    part_name_list = []
    part_name_dictTmp = {}
    cur.execute("select distinct part_name from ID_ADM.GPIM_PART_FORECAST where create_ym=(select max(create_ym) from ID_ADM.GPIM_PART_FORECAST)")
    for r in cur :
        part_name_list.append({'category': r[0], 'value': 0})
        part_name_dictTmp[r[0]] = 0
    forecast_list = []
    cur.execute("select rc_id,part_name,sum(adjust_forecast) c from ID_ADM.GPIM_PART_FORECAST where create_ym=(select max(create_ym) from ID_ADM.GPIM_PART_FORECAST) group by rc_id,part_name order by rc_id,c desc")
    c = 0
    rc_id = ''
    sum = 0
    tmp = {}
    tmp['subData'] = []
    for r in cur :
        if r[0] != rc_id and c > 0 :
            tmp['category'] = rc_id
            tmp['value'] = sum
            for k, v in part_name_dictTmp.items() :
                if v == 0 :
                    tmp['subData'].append({'category':k,'value':0})
            forecast_list.append(tmp)
            sum = 0
            tmp = {}
            tmp['subData'] = []
            for k in part_name_dictTmp :
                part_name_dictTmp[k] = 0
        rc_id = r[0]
        part_name = r[1]
        part_name_dictTmp[part_name] = 1
        adjust_forecast = r[2]
        #if int(adjust_forecast) > 0 :
        tmp['subData'].append({'category':part_name,'value':adjust_forecast})
        sum = sum + adjust_forecast
        c = c + 1
    tmp['category'] = rc_id
    for k, v in part_name_dictTmp.items() :
        if v == 0 :
            tmp['subData'].append({'category':k,'value':0})
    tmp['value'] = sum
    forecast_list.append(tmp)
    """
    adjust_forecast_list = {}
    cur.execute("select a.rc_id,a.product_id,a.part_name,NVL(a.part_no,'NA'),a.transfer_qty,NVL(a.plant,'NA'),a.adjust_forecast ,NVL(b.adjust_forecast, -1),a.create_ym from ID_ADM.GPIM_PART_FORECAST a left join (select rc_id,product_id ,part_name,part_no,adjust_forecast,create_ym from ID_ADM.GPIM_PART_FORECAST) b on a.rc_id=b.rc_id and a.product_id=b.product_id and a.part_name=b.part_name  and a.part_no=b.part_no and b.create_ym=TO_CHAR( add_months(trunc(TO_DATE(a.create_ym, 'YYYY-MM'),'mm'),-1), 'YYYY-MM') where a.create_ym > '2021-12' order by a.create_ym desc")
    c = 0
    for r in cur :
        tmp = {}
        tmp['rc_id'] = r[0]
        tmp['product_id'] = r[1]
        tmp['part_name'] = r[2]
        tmp['part_no'] = r[3]
        tmp['transfer_qty'] = r[4]
        tmp['plant'] = r[5]
        tmp['adjust_forecast1'] = r[6]
        tmp['adjust_forecast2'] = 'NA'   
        tmp['diff'] = 'NA'
        if int(r[7]) != -1 : 
            tmp['adjust_forecast2'] = r[7]
            tmp['diff'] = int(r[6]) - int(r[7])
        tmp['diff_percent'] = 'NA'
        if int(r[6]) >= 0 and int(r[7]) > 0 :
            #tmp['diff'] = int(r[6]) - int(r[7])
            tmp['diff_percent'] = str(round(100*(int(r[6]) - int(r[7]))/int(r[7]),2))+'%'
        tmp['create_ym'] = r[8]
        adjust_forecast_list[str(c)] = tmp
        c = c + 1
    data['forecast_list'] = forecast_list
    data['rc_id_list'] = rc_id_list
    data['adjust_forecast_list'] = adjust_forecast_list
    cur.close()
    con.close()
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
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    outfile_acc_list = {}
    cur = conn.cursor()
    cur.execute("select yyyymm,qty1,ta1,oes1,ues1,qty2,ta2,oes2,ues2,qty3,ta3,oes3,ues3,qty4,ta4,oes4,ues4 ,creationdate from re.outfile_acc order by yyyymm")
    c = 0
    for r in cur :
        tmp = {}
        tmp['yyyymm'] = r[0]
        tmp['qty1'] = r[1]
        tmp['ta1'] = r[2]
        tmp['oes1'] = r[3]
        tmp['ues1'] = r[4]
        tmp['qty2'] = r[5]
        tmp['ta2'] = r[6]
        tmp['oes2'] = r[7]
        tmp['ues2'] = r[8]
        tmp['qty3'] = r[9]
        tmp['ta3'] = r[10]
        tmp['oes3'] = r[11]
        tmp['ues3'] = r[12]
        tmp['qty4'] = r[13]
        tmp['ta4'] = r[14]
        tmp['oes4'] = r[15]
        tmp['ues4'] = r[16]
        outfile_acc_list[str(c)] = tmp
        c=c+1
    data['outfile_acc_list'] = outfile_acc_list
    cur.close()
    conn.close()
    
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    cur.execute("select max(issue_date) from RQ_ADM.GBIM_ISSUE_DATE")
    max_issue_date = datetime.strptime(cur.fetchone()[0]+'-10', '%Y-%m-%d')    
    issue_date = (max_issue_date - relativedelta(months=3)).strftime('%Y-%m')
    data['from_end'] = issue_date+'~'+max_issue_date.strftime('%Y-%m')
    yyyymm = (max_issue_date - relativedelta(months=3)).strftime('%Y%m')
    issue_date_list = {}
    cur.execute("select a.model_name,a.qty,NVL(TO_CHAR(b.predict_qty),'NA'),NVL(TO_CHAR(a.qty-b.predict_qty),'NA'),round((a.qty-b.predict_qty)/a.qty,2)*100||'%',ABS(round((a.qty-b.predict_qty)/a.qty,2)*100)||'%' from (select model_name ,sum(qty) qty from RQ_ADM.GBIM_ISSUE_DATE where issue_date >= :issue_date group by model_name ) a left join (select model_name, sum(predict_qty) predict_qty from RQ_ADM.GBIM_SMART_FR_PREDICT where yyyymm = :yyyymm group by model_name ) b on a.model_name = b.model_name order by a.model_name",{'issue_date':issue_date,'yyyymm':yyyymm})
    c = 0
    for r in cur :
        tmp = {}
        tmp['model_name'] = r[0]
        tmp['qty'] = r[1]
        tmp['predict_qty'] = r[2] 
        tmp['difference'] = r[3]
        tmp['percent'] = r[4]
        tmp['percent_abs'] = r[5]
        issue_date_list[str(c)] = tmp
        c=c+1
    data['issue_date_list'] = issue_date_list
    cur.close()
    con.close()
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

@app.route('/gbim/set_forecast_api', methods=['GET','POST'])
#@login_required
def set_forecast_api(): 
    data = {}
    data['userChineseName'] = session['userChineseName']
    whereStr = " where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' "
    whereDict = {}
    """
    MOTHER_MODEL_NAME = request.args.get("MOTHER_MODEL_NAME")
    
    if MOTHER_MODEL_NAME != '' :
        whereStr = whereStr + ' and MOTHER_MODEL_NAME=:MOTHER_MODEL_NAME '
        whereDict['MOTHER_MODEL_NAME'] = MOTHER_MODEL_NAME
    PHASE = request.args.get("PHASE")
    if PHASE != '' :
        whereStr = whereStr + " and PHASE=:PHASE "
        whereDict['PHASE'] = PHASE
    print('MOTHER_MODEL_NAME:',MOTHER_MODEL_NAME,',PHASE:',PHASE)
    """
    models_string = request.args.get("MOTHER_MODEL_NAME")    
    if models_string != '' :
        #models_list=models_string.split(', ')        
        whereStr = whereStr + " and MOTHER_MODEL_NAME in ("+models_string+")"
        #whereDict['models_list'] = (', '.join("'" + item + "'" for item in models_list ))
        #whereDict['models_list']=models_string
    phases_string = request.args.get("PHASE")
    if phases_string != '' :
        #phases_list=phases_string.split(', ')
        whereStr = whereStr + " and PHASE in ("+phases_string+")"
        #whereDict['phases_list'] = (', '.join("'" + item + "'" for item in phases_list ))
        #whereDict['phases_list']=phases_string
    print('models_string:',models_string,',phases_string:',phases_string)
    
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    # FCST_QTY_B 整新品，B grade
    # FCST_QTY_A 新品，A grade 
    # INVENTORY_B  整新品 RC 庫存
    # INVENTORY_A 新品 RC 庫存
    # ON_WAY_QTY On Way
    # RG_QTY RG RG
    # 平均月耗用 Check up(H+L)
    fcst_month = []
    FCST_QTY_B = []
    FCST_QTY_A = []
    INVENTORY_B = []
    INVENTORY_A = []
    ON_WAY_QTY = []
    RG_QTY = []
    COMSUMPTION_AVG = []
    sql="select TO_CHAR(a.fcst_month, 'YYYY/MM') fcst_month,a.FCST_QTY_B,a.FCST_QTY_A,a.INVENTORY_B,a.INVENTORY_A,a.ON_WAY_QTY,a.RG_QTY,b.COMSUMPTION_AVG, max_fcst_month from (select fcst_month,sum(FCST_QTY_B) FCST_QTY_B,sum(FCST_QTY_A) FCST_QTY_A,sum(INVENTORY_B) INVENTORY_B,sum(INVENTORY_A) INVENTORY_A,sum(ON_WAY_QTY) ON_WAY_QTY,sum(RG_QTY) RG_QTY from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr+" GROUP by fcst_month) a left join (select fcst_month, sum(COMSUMPTION_AVG_A)+sum(COMSUMPTION_AVG_B) COMSUMPTION_AVG from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP "+whereStr+" GROUP by fcst_month) b on a.fcst_month = b.fcst_month left join (select max(TO_CHAR(fcst_month, 'YYYY/MM')) max_fcst_month from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr+") c on 1=1 order by a.fcst_month asc"
    data['models_string']=models_string
    data['phases_string']=phases_string
    data['sql']=sql
    #return data
    cur.execute("select TO_CHAR(a.fcst_month, 'YYYY/MM') fcst_month,a.FCST_QTY_B,a.FCST_QTY_A,a.INVENTORY_B,a.INVENTORY_A,a.ON_WAY_QTY,a.RG_QTY,b.COMSUMPTION_AVG, max_fcst_month from (select fcst_month,sum(FCST_QTY_B) FCST_QTY_B,sum(FCST_QTY_A) FCST_QTY_A,sum(INVENTORY_B) INVENTORY_B,sum(INVENTORY_A) INVENTORY_A,sum(ON_WAY_QTY) ON_WAY_QTY,sum(RG_QTY) RG_QTY from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr+" GROUP by fcst_month) a left join (select fcst_month, sum(COMSUMPTION_AVG_A)+sum(COMSUMPTION_AVG_B) COMSUMPTION_AVG from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP "+whereStr+" GROUP by fcst_month) b on a.fcst_month = b.fcst_month left join (select max(TO_CHAR(fcst_month, 'YYYY/MM')) max_fcst_month from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr+") c on 1=1 order by a.fcst_month asc")
    
    for r in cur :
        max_fcst_month = r[8]
        fcst_month.append(r[0])
        FCST_QTY_B.append(r[1])
        FCST_QTY_A.append(r[2])
        INVENTORY_B.append(r[3])
        INVENTORY_A.append(r[4])        
        #ON_WAY_QTY.append(r[5])
        ON_WAY_QTY.append(r[5]) if r[0] == max_fcst_month else ON_WAY_QTY.append(0)
        #RG_QTY.append(r[6])
        RG_QTY.append(r[6]) if r[0] == max_fcst_month else RG_QTY.append(0)
        COMSUMPTION_AVG.append(r[7])
    fcst_month_search = sorted(fcst_month, reverse = True)
    fcst_month.append('新品')
    fcst_month.append('整新品')
    FCST_QTY_B.append(0)
    FCST_QTY_B.append(r[1])
    FCST_QTY_A.append(r[2])
    FCST_QTY_A.append(0)
    INVENTORY_B.append(0)
    INVENTORY_B.append(r[3])
    INVENTORY_A.append(r[4])
    INVENTORY_A.append(0)
    ON_WAY_QTY.append(r[5])
    ON_WAY_QTY.append(0)
    RG_QTY.append(r[6])
    RG_QTY.append(0)
    #COMSUMPTION_AVG.append(0)
    #COMSUMPTION_AVG.append(0)    
    data['fcst_month_search'] = fcst_month_search
    data['fcst_month'] = fcst_month
    data['FCST_QTY_B'] = FCST_QTY_B
    data['FCST_QTY_A'] = FCST_QTY_A
    data['INVENTORY_B'] = INVENTORY_B
    data['INVENTORY_A'] = INVENTORY_A
    data['ON_WAY_QTY'] = ON_WAY_QTY
    data['RG_QTY'] = RG_QTY
    data['COMSUMPTION_AVG'] = COMSUMPTION_AVG
    return data

@app.route('/gbim/set_forecast', methods=['GET'])
@login_required
def set_forecast():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"整機-備品-Forecast"
    }
    data['userChineseName'] = session['userChineseName']
    
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    # FCST_QTY_B 整新品，B grade
    # FCST_QTY_A 新品，A grade 
    # INVENTORY_B  整新品 RC 庫存
    # INVENTORY_A 新品 RC 庫存
    # ON_WAY_QTY On Way
    # RG_QTY RG RG
    # 平均月耗用 Check up(H+L)
    fcst_month = []
    FCST_QTY_B = []
    FCST_QTY_A = []
    INVENTORY_B = []
    INVENTORY_A = []
    ON_WAY_QTY = []
    RG_QTY = []
    COMSUMPTION_AVG = []
    #cur.execute("select TO_CHAR(a.fcst_month, 'YYYY/MM' ) fcst_month,a.FCST_QTY_B,a.FCST_QTY_A,a.INVENTORY_B,a.INVENTORY_A,a.ON_WAY_QTY,a.RG_QTY,b.COMSUMPTION_AVG from (select fcst_month,sum(FCST_QTY_B) FCST_QTY_B,sum(FCST_QTY_A) FCST_QTY_A,sum(INVENTORY_B) INVENTORY_B,sum(INVENTORY_A) INVENTORY_A,sum(ON_WAY_QTY) ON_WAY_QTY,sum(RG_QTY) RG_QTY from RQ_ADM.VIZIO_FCST_OUTPUT where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' GROUP by fcst_month) a left join (select fcst_month, sum(COMSUMPTION_AVG_A)+sum(COMSUMPTION_AVG_B) COMSUMPTION_AVG from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' GROUP by fcst_month) b on a.fcst_month = b.fcst_month order by a.fcst_month asc")
    cur.execute("select distinct TO_CHAR(fcst_month, 'YYYY/MM' ) fcst_month from RQ_ADM.VIZIO_FCST_OUTPUT where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' order by fcst_month asc")
    for r in cur :
        fcst_month.append(r[0])
        """FCST_QTY_B.append(r[1])
        FCST_QTY_A.append(r[2])
        INVENTORY_B.append(r[3])
        INVENTORY_A.append(r[4])
        ON_WAY_QTY.append(r[5])
        RG_QTY.append(r[6])
        COMSUMPTION_AVG.append(r[7])"""
    fcst_month_search = sorted(fcst_month, reverse = True)
    fcst_month.append('新品')
    fcst_month.append('整新品')
    """
    FCST_QTY_B.append(0)
    FCST_QTY_B.append(r[1])
    FCST_QTY_A.append(r[2])
    FCST_QTY_A.append(0)
    INVENTORY_B.append(0)
    INVENTORY_B.append(r[3])
    INVENTORY_A.append(r[4])
    INVENTORY_A.append(0)
    ON_WAY_QTY.append(r[5])
    ON_WAY_QTY.append(0)
    RG_QTY.append(r[6])
    RG_QTY.append(0) """
    data['fcst_month_search'] = fcst_month_search
    data['fcst_month'] = fcst_month
    """data['FCST_QTY_B'] = FCST_QTY_B
    data['FCST_QTY_A'] = FCST_QTY_A
    data['INVENTORY_B'] = INVENTORY_B
    data['INVENTORY_A'] = INVENTORY_A
    data['ON_WAY_QTY'] = ON_WAY_QTY
    data['RG_QTY'] = RG_QTY
    data['COMSUMPTION_AVG'] = COMSUMPTION_AVG"""
    MOTHER_MODEL_NAME_set = set()
    fcst_output_list = {}
    cur.execute("select TO_CHAR(FCST_MONTH, 'YYYY/MM' ),NVL(MOTHER_MODEL_NAME,'NA'),NVL(MODEL_NAME,'NA'),NVL(PHASE,'NA'),NVL(FCST_QTY_A,-9999),NVL(INVENTORY_A,-9999),NVL(ON_WAY_QTY,-9999),NVL(RG_QTY,-9999),NVL(ALERT_INVENTORY,-9999),NVL(TRANSFER_QTY_A,-9999),NVL(FCST_QTY_B,-9999),NVL(INVENTORY_B,-9999),NVL(TRANSFER_QTY_B,-9999),(select max(TO_CHAR(FCST_MONTH, 'YYYY/MM')) from RQ_ADM.VIZIO_FCST_OUTPUT) from RQ_ADM.VIZIO_FCST_OUTPUT order by FCST_MONTH desc")
    c = 0
    for r in cur :
        tmp = {}
        max_fcst_month = r[13]
        tmp['FCST_MONTH'] = r[0]
        tmp['MOTHER_MODEL_NAME'] = r[1] if r[1] != 'NA' else ''
        MOTHER_MODEL_NAME_set.add(tmp['MOTHER_MODEL_NAME'])
        tmp['MODEL_NAME'] = r[2] if r[2] != 'NA' else ''
        tmp['PHASE'] = r[3] if r[3] != 'NA' else ''
        tmp['FCST_QTY_A'] = r[4] if int(r[4]) != -9999 else ''
        tmp['INVENTORY_A'] = r[5] if int(r[5]) != -9999 else ''
        #tmp['ON_WAY_QTY'] = r[6] if int(r[6]) != -9999 else ''
        #tmp['RG_QTY'] = r[7] if int(r[7]) != -9999 else ''
        if r[0] == max_fcst_month :
            tmp['ON_WAY_QTY'] = r[6] if int(r[6]) != -9999 else ''
            tmp['RG_QTY'] = r[7] if int(r[7]) != -9999 else ''
        else :
            tmp['ON_WAY_QTY'] = ''
            tmp['RG_QTY'] = ''
        tmp['ALERT_INVENTORY'] = r[8] if int(r[8]) != -9999 else ''
        tmp['TRANSFER_QTY_A'] = r[9] if int(r[9]) != -9999 else ''
        tmp['FCST_QTY_B'] = r[10] if int(r[10]) != -9999 else ''
        tmp['INVENTORY_B'] = r[11] if int(r[11]) != -9999 else ''
        tmp['TRANSFER_QTY_B'] = r[12] if int(r[12]) != -9999 else ''
        
        fcst_output_list[str(c)] = tmp
        c = c + 1
    data['fcst_output_list'] = fcst_output_list
    data['MOTHER_MODEL_NAME_set'] = sorted(MOTHER_MODEL_NAME_set)
    cur.close()
    con.close()
    return render_template('set_forecast.html', data = data)

@app.route('/gbim/set_audit_api', methods=['GET'])
#@login_required
def set_audit_api():
    data = {}
    data['userChineseName'] = session['userChineseName']
    whereStr1 = " where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' "
    whereStr2 = " where 1=1 "
    whereDict = {}
    MOTHER_MODEL_NAME = request.args.get("MOTHER_MODEL_NAME")    
    if MOTHER_MODEL_NAME != '' :
        whereStr1 = whereStr1 + ' and MOTHER_MODEL_NAME=:MOTHER_MODEL_NAME '
        whereStr2 = whereStr2 + ' and MOTHER_MODEL_NAME=:MOTHER_MODEL_NAME '
        whereDict['MOTHER_MODEL_NAME'] = MOTHER_MODEL_NAME
    PHASE = request.args.get("PHASE")
    if PHASE != '' :
        whereStr1 = whereStr1 + ' and PHASE=:PHASE '
        whereStr2 = whereStr2 + ' and PHASE=:PHASE '
        whereDict['PHASE'] = PHASE
    print('MOTHER_MODEL_NAME:',MOTHER_MODEL_NAME,',PHASE:',PHASE)
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    cur1 = con.cursor()
    COMSUMPTION = []
    fcst_month = []
    FCST_QTY = []
    upper_bound = []
    lower_bound = []
    cur.execute("select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(COMSUMPTION_N4_A+COMSUMPTION_N2_B) COMSUMPTION from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP "+whereStr1+" group by fcst_month order by fcst_month",whereDict)
    for r in cur : 
        fcst_month.append(r[0])
        COMSUMPTION.append(r[1])
        fcst_month_4 = (datetime.strptime(r[0], '%Y/%m') - relativedelta(months=4)).strftime("%Y/%m")
        whereDict['fcst_month']=fcst_month_4
        #cur1.execute("select FCST_QTY,upper_bound_a+upper_bound_b,lower_bound_a+lower_bound_b from (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(FCST_QTY_A)+sum(FCST_QTY_B) FCST_QTY from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr2+" group by fcst_month) a left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_a ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_a from RQ_ADM.VIZIO_A_GRADE_PREDICT GROUP by fcst_month) c on a.fcst_month = c.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_b ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_b from RQ_ADM.VIZIO_B_GRADE_PREDICT GROUP by fcst_month) d on a.fcst_month = d.fcst_month where a.fcst_month=:fcst_month",whereDict)
        cur1.execute("select FCST_QTY,NVL(upper_bound_a, 0)+NVL(upper_bound_b, 0),NVL(lower_bound_a, 0)+NVL(lower_bound_b, 0) from (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(FCST_QTY_A)+sum(FCST_QTY_B) FCST_QTY from RQ_ADM.VIZIO_FCST_OUTPUT "+whereStr2+" group by fcst_month) a left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_a ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_a from RQ_ADM.VIZIO_A_GRADE_PREDICT GROUP by fcst_month) c on a.fcst_month = c.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_b ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_b from RQ_ADM.VIZIO_B_GRADE_PREDICT GROUP by fcst_month) d on a.fcst_month = d.fcst_month where a.fcst_month=:fcst_month",whereDict)        
        """
        for r1 in cur1 :
            FCST_QTY.append(r1[0])
            upper_bound.append(r1[1])
            lower_bound.append(r1[2])
            
        """ 
        cur1_ = cur1.fetchall()
        if len(cur1_) > 0 :
            for r1 in cur1_ :            
                print(fcst_month_4,' => ',r1[0],' , ',r1[1],' , ', r1[2])
                FCST_QTY.append(r1[0])                
                upper_bound.append(r1[1])
                lower_bound.append(r1[2]) 
        else :
            print(fcst_month_4,' => 0 , 0 , 0')
            FCST_QTY.append(0)                
            upper_bound.append(0)
            lower_bound.append(0)    
            #print('fcst_month_4:',fcst_month_4,' , upper_bound:',upper_bound)
            
    #print('upper_bound:')
    #print(upper_bound)
    #print('lower_bound:')
    #print(lower_bound)
    data['fcst_month'] = fcst_month
    data['COMSUMPTION'] = COMSUMPTION
    data['FCST_QTY'] = FCST_QTY
    data['upper_bound'] = upper_bound
    data['lower_bound'] = lower_bound
    return data

@app.route('/gbim/set_audit', methods=['GET'])
@login_required
def set_audit():
    data = {
        "title": "RQM庫存預測平台",
        "body": "Flask simple MVC",
        "page_router":"整機-備品-檢核"
    }
    data['userChineseName'] = session['userChineseName']
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    cur1 = con.cursor()
    # Sell through:VIZIO_SELL_THRU_2020_01 - 2021_12.xlsx <==每月提供
    fcst_month = []
    FCST_QTY = []    
    upper_bound = []
    lower_bound = []
    COMSUMPTION = [] 
    #cur.execute("select a.fcst_month,FCST_QTY,upper_bound_a+upper_bound_b,lower_bound_a+lower_bound_b,b.COMSUMPTION from (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(FCST_QTY_A)+sum(FCST_QTY_B) FCST_QTY from RQ_ADM.VIZIO_FCST_OUTPUT where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' group by fcst_month) a left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(COMSUMPTION_N4_A+COMSUMPTION_N2_B) COMSUMPTION from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP group by TO_CHAR(fcst_month, 'YYYY/MM')) b on a.fcst_month=b.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_a ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_a from RQ_ADM.VIZIO_A_GRADE_PREDICT GROUP by fcst_month) c on a.fcst_month = c.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_b ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_b from RQ_ADM.VIZIO_B_GRADE_PREDICT GROUP by fcst_month) d on a.fcst_month = d.fcst_month order by a.fcst_month")
    cur.execute("select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(COMSUMPTION_N4_A+COMSUMPTION_N2_B) COMSUMPTION from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP where TO_CHAR(fcst_month, 'YYYY/MM')>='2022/01' group by fcst_month order by fcst_month")
    
    for r in cur :
        fcst_month.append(r[0])
        COMSUMPTION.append(r[1]) 
        fcst_month_4 = (datetime.strptime(r[0], '%Y/%m') - relativedelta(months=4)).strftime("%Y/%m")
        #cur1.execute("select FCST_QTY,upper_bound_a+upper_bound_b,lower_bound_a+lower_bound_b from (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(FCST_QTY_A)+sum(FCST_QTY_B) FCST_QTY from RQ_ADM.VIZIO_FCST_OUTPUT  group by fcst_month) a left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_a ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_a from RQ_ADM.VIZIO_A_GRADE_PREDICT GROUP by fcst_month) c on a.fcst_month = c.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_b ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_b from RQ_ADM.VIZIO_B_GRADE_PREDICT GROUP by fcst_month) d on a.fcst_month = d.fcst_month where a.fcst_month=:fcst_month",{'fcst_month':fcst_month_4})
        cur1.execute("select FCST_QTY,NVL(upper_bound_a, 0)+NVL(upper_bound_b, 0),NVL(lower_bound_a, 0)+NVL(lower_bound_b, 0) from (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(FCST_QTY_A)+sum(FCST_QTY_B) FCST_QTY from RQ_ADM.VIZIO_FCST_OUTPUT  group by fcst_month) a left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_a ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_a from RQ_ADM.VIZIO_A_GRADE_PREDICT GROUP by fcst_month) c on a.fcst_month = c.fcst_month left join (select TO_CHAR(fcst_month, 'YYYY/MM') fcst_month,sum(CASE WHEN upper_bound < 0 THEN 0 ELSE upper_bound END) upper_bound_b ,sum(CASE WHEN lower_bound < 0 THEN 0 ELSE lower_bound END) lower_bound_b from RQ_ADM.VIZIO_B_GRADE_PREDICT GROUP by fcst_month) d on a.fcst_month = d.fcst_month where a.fcst_month=:fcst_month",{'fcst_month':fcst_month_4})
        
        for r1 in cur1 :            
            #print(fcst_month_4,' => ',r1[0],' , ',r1[1],' , ', r1[2])
            FCST_QTY.append(r1[0])                
            upper_bound.append(r1[1])
            lower_bound.append(r1[2])  
    fcst_month_search = sorted(fcst_month, reverse = True)
    data['fcst_month_search'] = fcst_month_search
    data['fcst_month'] = fcst_month
    #data['FCST_QTY'] = FCST_QTY
    #print(FCST_QTY)
    #data['upper_bound'] = upper_bound
    #data['lower_bound'] = lower_bound
    data['COMSUMPTION'] = COMSUMPTION
    
    fcst_output_checkup_list = {}
    cur.execute("select TO_CHAR(FCST_MONTH, 'YYYY/MM' ),NVL(MOTHER_MODEL_NAME,'NA'),NVL(MODEL_NAME,'NA'),NVL(PHASE,'NA'),NVL(TRANSFER_N4,-9999),NVL(COMSUMPTION_N4_A,-9999),NVL(COMSUMPTION_A,-9999),NVL(COMSUMPTION_AVG_A,-9999),NVL(TRANSFER_N2,-9999),NVL(COMSUMPTION_N2_B,-9999),NVL(COMSUMPTION_B,-9999),NVL(COMSUMPTION_AVG_B,-9999) from RQ_ADM.VIZIO_FCST_OUTPUT_CHECKUP order by FCST_MONTH desc")
    c = 0
    for r in cur :
        tmp = {}
        tmp['FCST_MONTH'] = r[0]
        tmp['MOTHER_MODEL_NAME'] = r[1] if r[1] != 'NA' else ''
        tmp['MODEL_NAME'] = r[2] if r[2] != 'NA' else ''
        tmp['PHASE'] = r[3] if r[3] != 'NA' else ''
        tmp['TRANSFER_N4'] = r[4] if int(r[4]) != -9999 else ''
        tmp['COMSUMPTION_N4_A'] = r[5] if int(r[5]) != -9999 else ''
        tmp['COMSUMPTION_A'] = r[6] if int(r[6]) != -9999 else ''
        tmp['COMSUMPTION_AVG_A'] = r[7] if int(r[7]) != -9999 else ''
        tmp['TRANSFER_N2'] = r[8] if int(r[8]) != -9999 else ''
        tmp['COMSUMPTION_N2_B'] = r[9] if int(r[9]) != -9999 else ''
        tmp['COMSUMPTION_B'] = r[10] if int(r[10]) != -9999 else ''
        tmp['COMSUMPTION_AVG_B'] = r[11] if int(r[11]) != -9999 else ''
        fcst_output_checkup_list[str(c)] = tmp
        c = c + 1
    data['fcst_output_checkup_list'] = fcst_output_checkup_list
    cur.close()
    con.close()
    return render_template('set_audit.html', data = data)

@app.route('/gbim/ftp_rpt', methods=['GET'])
@login_required
def ftp_rpt(): 
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"整機-FTP-報表"
    }
    data['userChineseName'] = session['userChineseName']
    #con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    #cur = con.cursor()
    #cur.execute("")
    return render_template('ftp_rpt.html', data = data)

@app.route('/gbim/set_material_api_1', methods=['GET'])
#@login_required
def set_material_api_1():
    data = {}  
    material_item_string = request.args.get("material_item")    
    whereStr = "" 
    if material_item_string != '' :
        whereStr = whereStr + " and material_item in ("+material_item_string+")" 
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    cur1 = con.cursor()
    material_list = [] 
    cur1.execute("select distinct TO_CHAR(FCST_MONTH, 'YYYY/MM') from RQ_ADM.VIZIO_FCST_OUTPUT_2 order by TO_CHAR(FCST_MONTH, 'YYYY/MM')")
    #c=0
    for r1 in cur1 :
        FCST_MONTH = r1[0]
        cur.execute("select CONCAT('庫存-',material_item),sum(inventory)+sum(ON_WAY_QTY) from RQ_ADM.VIZIO_FCST_OUTPUT_2 where TO_CHAR(FCST_MONTH, 'YYYY/MM')= :FCST_MONTH "+whereStr+" group by material_item,FCST_MONTH order by FCST_MONTH,material_item",{'FCST_MONTH':FCST_MONTH})
        tmp = {}
        for r in cur :
            tmp[r[0]] = r[1]
        #tmp['fcst_month'] = FCST_MONTH
        #material_list[c] = tmp 
        #c=c+1
        cur.execute("select CONCAT('預測-',material_item), sum(FCST_QTY) from RQ_ADM.VIZIO_FCST_OUTPUT_2 where TO_CHAR(FCST_MONTH, 'YYYY/MM')= :FCST_MONTH "+whereStr+" group by material_item,FCST_MONTH order by FCST_MONTH,material_item",{'FCST_MONTH':FCST_MONTH})
        #tmp = {}
        for r in cur :
            tmp[r[0]] = r[1]
        tmp['fcst_month'] = FCST_MONTH
        material_list.append(tmp)  
        #c=c+1 
    data['material_list'] = material_list
    cur.close()
    cur1.close()
    con.close()
    return data

@app.route('/gbim/set_material_api_2', methods=['GET'])
#@login_required
def set_material_api_2():
    data = {}  
    vizio_model_string = request.args.get("vizio_model")   
    whereStr = " " 
    if vizio_model_string == "'空值'" :
        whereStr = whereStr + " and vizio_model is NULL "
    elif '空值' in vizio_model_string :
        whereStr = whereStr + " and (vizio_model in ("+vizio_model_string+") or vizio_model is NULL) " 
    elif vizio_model_string != '' :
        whereStr = whereStr + " and vizio_model in ("+vizio_model_string+")" 

    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor() 
    material_item = []
    inventory = []
    fcst_qty = []
    sqlstr = "select material_item, sum(inventory)+sum(ON_WAY_QTY)-sum(FCST_QTY),sum(FCST_QTY) from RQ_ADM.VIZIO_FCST_OUTPUT_2 where fcst_month=(select max(FCST_MONTH) from RQ_ADM.VIZIO_FCST_OUTPUT_2) "+whereStr+" group by material_item order by material_item"
    cur.execute(sqlstr)
    for r in cur : 
        material_item.append(r[0])
        inventory.append(r[1])
        fcst_qty.append(r[2]) 
    data['material_item'] = material_item
    data['inventory'] = inventory
    data['fcst_qty'] = fcst_qty
    data['sqlstr'] = sqlstr
    cur.close()
    con.close()
    return data

@app.route('/gbim/set_material', methods=['GET'])
@login_required
def set_material():
    data = {
        "title": "Hello World",
        "body": "Flask simple MVC",
        "page_router":"整機-料件"
    }
    data['userChineseName'] = session['userChineseName']
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    
    fcst_month = []
    cur.execute("select distinct TO_CHAR(fcst_month, 'YYYY/MM' ) fcst_month from RQ_ADM.VIZIO_FCST_OUTPUT_2 order by fcst_month asc")
    for r in cur :
        fcst_month.append(r[0])
    fcst_month_search = sorted(fcst_month, reverse = True)
    data['fcst_month_search'] = fcst_month_search
    
    set_material_list = {}
    material_item_set = set()
    vizio_model_set = set()
    cur.execute("select TO_CHAR(fcst_month, 'YYYY/MM'),groupcode,material_item,NVL(fcst_qty,-9999),NVL(inventory,-9999),NVL(on_way_qty,-9999),NVL(alert_inventory,-9999),NVL(transfer_qty,-9999),NVL(vizio_model,'NA') from RQ_ADM.VIZIO_FCST_OUTPUT_2 order by TO_CHAR(fcst_month, 'YYYY/MM') ")
    c = 0
    for r in cur :
        tmp = {}
        tmp['fcst_month'] = r[0]
        tmp['groupcode'] = r[1]
        tmp['material_item'] = r[2]
        material_item_set.add(tmp['material_item'])
        tmp['fcst_qty'] = r[3] if int(r[3]) != -9999 else ''
        tmp['inventory'] = r[4] if int(r[4]) != -9999 else ''
        tmp['on_way_qty'] = r[5] if int(r[5]) != -9999 else ''
        tmp['alert_inventory'] = r[6] if int(r[6]) != -9999 else ''
        tmp['transfer_qty'] = r[7] if int(r[7]) != -9999 else ''
        tmp['vizio_model'] = r[8] if r[8] != 'NA' else '空值'
        #if tmp['vizio_model'] != '' :
        vizio_model_set.add(tmp['vizio_model'])
        set_material_list[str(c)] = tmp
        c = c + 1
    data['set_material_list'] = set_material_list
    data['material_item_set'] = sorted(material_item_set)
    data['vizio_model_set'] = sorted(vizio_model_set)
    cur.close()
    con.close()
    return render_template('set_material.html', data = data)
## 葉瑞賢 #################################################################################

@app.route('/gbim/indexes', methods=['GET'])
@login_required
def indexes():
    data = {
        "title": "CoPQ四大指標",
        "body": "Flask simple MVC",
        "page_router":"CoPQ四大指標"
    }
    data['userChineseName'] = session['userChineseName']
    con = pymysql.connect(host=Database.rmadb['host'], port=Database.rmadb['port'],user=Database.rmadb['user'], passwd=Database.rmadb['passwd'], db=Database.rmadb['db'])
    cur = con.cursor()
    if request.method == 'POST':
        year = request.form['year']
        yearFrom = year+'00'
        yearTo = str(int(year)+1)+'00'
    else :
        cur.execute("SELECT max(yearmonth) FROM copq_indexes")
        year = cur.fetchone()[0]
        yearFrom = year+'00'
        yearTo = str(int(year)+1)+'00'
    data['year'] = year
    
    cur.execute("")
    
    data['userChineseName'] = session['userChineseName']
    cur.close()
    con.close()
    
    return render_template('indexes.html', data = data)

#======== 維修效益 陳筱蓉
@app.route('/gbim/mapping', methods=['GET','POST'])
@login_required
def mapping():
    data = {
        "title": "mapping table",
        "formURL": "http://"+dbconfig.serverip+"/gbim/mapping",
        "result": getMappingResult(),
        "creationdate": getCreationdate(),
        "page_router":"mapping table"
    } 
    if request.method == 'POST': 
        print(request.files['MappingFile'])
        MappingFile = request.files['MappingFile']
        resultCount = parseExcelToMappingTable(MappingFile)
        data['result'] = getMappingResult() #resultCount
        data['creationdate'] = getCreationdate()
    data['userChineseName'] = session['userChineseName']
    return render_template('mapping.html', data = data)
 
@app.route('/gbim/filter', methods=['GET','POST'])
@login_required
def filter():
    data = {
        "title": "維修效益物料使用差異",
        "formURL": "http://"+dbconfig.serverip+":30083/gbim/filter",
        "result": getFilterResult(),
        #"creationdate": getCreationdate(),
        "page_router":"維修效益物料使用差異"
    } 
    if request.method == 'POST': 
        FilterFile = request.files['FilterFile']
        resultCount = parseExcelToFilterTable(FilterFile)
        data['result'] = getFilterResult()
    data['userChineseName'] = session['userChineseName']
    return render_template('filter.html', data = data)
def getMappingResult() :
    result = {'mapping_Defect_Type':[0,''],'mapping_Parts_Type':[0,''],'mapping_RC_ID':[0,''],'mapping_Size_Range':[0,''],'mapping_Defect_Group':[0,''],'mapping_Defect_no_Parts':[0,''],'mapping_Parts_Cost':[0,''],'mapping_RC_Cost_iEP_PR':[0,''],'mapping_Price_Normal':[0,''],'mapping_Price_DoS':[0,'']}    
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    for r in result :
        cur.execute("select count(1) from "+r)
        result[r][0] = cur.fetchone()[0]
        if result[r][0] > 0 :
            cur.execute("select creationdate from "+r+" limit 1")
            result[r][1] = cur.fetchone()[0]
    return result
def getCreationdate() :
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    cur.execute("select creationdate from mapping_Defect_Type limit 1")   
    creationdate = cur.fetchone()[0]
    return creationdate

def getMappingResult() :
    result = {'mapping_Defect_Type':[0,''],'mapping_Parts_Type':[0,''],'mapping_RC_ID':[0,''],'mapping_Size_Range':[0,''],'mapping_Defect_Group':[0,''],'mapping_Defect_no_Parts':[0,''],'mapping_Parts_Cost':[0,''],'mapping_RC_Cost_iEP_PR':[0,''],'mapping_Price_Normal':[0,''],'mapping_Price_DoS':[0,'']}
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    for r in result :
        cur.execute("select count(1) from "+r)
        result[r][0] = cur.fetchone()[0]
        if result[r][0] > 0 :
            cur.execute("select creationdate from "+r+" limit 1")
            result[r][1] = cur.fetchone()[0]
    return result

def getFilterResult() :
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    result = {}
    cur.execute("select TO_CHAR(create_date, 'YYYY/MM/DD'),count(1) from id_adm.z_bogrm_repair_finish_yearly group by TO_CHAR(create_date, 'YYYY/MM/DD')")	
    for r in cur :
        result[r[0]] = r[1]
    return result

def parseExcelToFilterTable(FilterFile) :
    con = cx_Oracle.connect(dbconfig.qintpotlDB, encoding="UTF-8", nencoding="UTF-8")
    cur = con.cursor()
    dt1 = datetime.utcnow().replace(tzinfo=timezone.utc)
    creationdate = dt1.astimezone(timezone(timedelta(hours=8))).strftime('%Y/%m/%d %H:%M:%S')

    data_xls = pd.read_excel(FilterFile, sheet_name='差異RawData', header = 0).fillna('')
    resultCount = 0
    for index,row in data_xls[['ORDER_NO','SERIAL_NO','SYMPTOM','PART_NO']].iterrows() :
        ORDER_NO = row['ORDER_NO']
        SERIAL_NO = row['SERIAL_NO']
        SYMPTOM = row['SYMPTOM']
        PART_NO = row['PART_NO']
        print(index,' ',ORDER_NO,SERIAL_NO,SYMPTOM,PART_NO)		
        
        cur.execute("select count(1) from id_adm.z_bogrm_repair_finish_yearly where ORDER_NO=:ORDER_NO and SERIAL_NO=:SERIAL_NO and SYMPTOM=:SYMPTOM and PART_NO=:PART_NO",{'ORDER_NO':ORDER_NO,'SERIAL_NO':SERIAL_NO,'SYMPTOM':SYMPTOM,'PART_NO':PART_NO})
        if cur.fetchone()[0] == 0:
            resultCount = resultCount + 1
            print(index,ORDER_NO,SERIAL_NO,SYMPTOM,PART_NO)
            cur.execute("insert into id_adm.z_bogrm_repair_finish_yearly (ORDER_NO,SERIAL_NO,SYMPTOM,PART_NO,CREATE_DATE) values(:ORDER_NO,:SERIAL_NO,:SYMPTOM,:PART_NO,:CREATE_DATE)",{'ORDER_NO':ORDER_NO,'SERIAL_NO':SERIAL_NO,'SYMPTOM':SYMPTOM,'PART_NO':PART_NO,'CREATE_DATE':datetime.now()})
            cur.execute("commit")
    print('寫入',resultCount,'筆')
    cur.execute("commit")
    cur.close()
    con.close()
    return resultCount

def parseExcelToMappingTable(MappingFile) :
    resultCount = {'mapping_Defect_Type':0,'mapping_Parts_Type':0,'mapping_RC_ID':0,'mapping_Size_Range':0,'mapping_Defect_Group':0,'mapping_Defect_no_Parts':0,'mapping_Parts_Cost':0,'mapping_RC_Cost_iEP_PR':0,'mapping_Price_Normal':0,'mapping_Price_DoS':0}
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    dt1 = datetime.utcnow().replace(tzinfo=timezone.utc)
    creationdate = dt1.astimezone(timezone(timedelta(hours=8))).strftime('%Y/%m/%d %H:%M:%S')
    
    #MappingFile = 'Mapping Table to IDD.xlsx'
    xls = pd.ExcelFile(MappingFile)
    # sheet 3. RC Cost iEP PR 報價 ######################################################################################
    data_xls = pd.read_excel(xls, sheet_name='RC Cost iEP PR 報價', header = 1).fillna('')
    #data_xls = pd.read_excel(MappingFile, sheet_name='RC Cost iEP PR', header = 1).fillna('')
    c = 0
    sqlString = 'insert into re.mapping_RC_Cost_iEP_PR(NAME,USD,creationdate)values'
    for index,row in data_xls[['NAME','USD']].iterrows():
        if row['NAME'] != '':
            sqlString = sqlString+"('"+row['NAME']+"','"+str(row['USD'])+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_RC_Cost_iEP_PR")
        #cur.execute("ALTER TABLE re.mapping_RC_Cost_iEP_PR AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_RC_Cost_iEP_PR'] = c
        
    print('3. RC Cost iEP PR 報價 ',c,'筆')      
    cur.execute(sqlString)
    cur.execute('commit')
    # sheet 1. MAPPING ######################################################################################
    data_xls = pd.read_excel(xls, sheet_name='MAPPING', header = 1).fillna('')

    # 1.1 Defect Type
    c = 0
    sqlString = 'insert into re.mapping_Defect_Type(SYMPTOM,Defect_Type,creationdate)values'
    for index,row in data_xls[['SYMPTOM','Defect Type']].iterrows() :
        if row['SYMPTOM'] != '' :
            sqlString = sqlString+"('"+row['SYMPTOM']+"','"+row['Defect Type']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        #cur.execute("delete from re.mapping_Defect_Type")
        cur.execute("TRUNCATE re.mapping_Defect_Type") 
        #cur.execute("ALTER TABLE re.mapping_Defect_Type AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Defect_Type'] = c

    print('1.1 Defect Type ',c,'筆')
    cur.execute(sqlString)
    cur.execute('commit')
    # 1.2 Parts Type
    c = 0
    sqlString = 'insert into re.mapping_Parts_Type(PART_NO,Parts_Type,creationdate)values'
    for index,row in data_xls[['PART_NO','Parts Type']].iterrows():
        if row['PART_NO'] != '':
            sqlString = sqlString+"('"+str(row['PART_NO'])+"','"+row['Parts Type']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_Parts_Type")
        #cur.execute("ALTER TABLE re.mapping_Parts_Type AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Parts_Type'] = c
        
    print('1.2 Parts Type ',c,'筆')      
    cur.execute(sqlString)
    cur.execute('commit')
    # 1.3 RC ID
    c = 0
    sqlString = 'insert into re.mapping_RC_ID(RC_ID,RCID,creationdate)values'
    for index,row in data_xls[['RC_ID','RC ID']].iterrows():
        if row['RC_ID'] != '':
            sqlString = sqlString+"('"+row['RC_ID']+"','"+row['RC ID']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :        
        cur.execute("TRUNCATE re.mapping_RC_ID")
        #cur.execute("ALTER TABLE re.mapping_RC_ID AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_RC_ID'] = c
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    print('1.3 RC ID ',c,'筆')
    cur.execute(sqlString)
    cur.execute('commit')
    # 1.4 Size Range
    c = 0
    sqlString = 'insert into re.mapping_Size_Range(`from`,`to`,Size_range,creationdate)values'
    for index,row in data_xls[['from','to','Size range']].iterrows():
        if row['Size range'] != '':
            sqlString = sqlString+"('"+str(row['from'])+"','"+str(row['to'])+"','"+row['Size range']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_Size_Range")
        #cur.execute("ALTER TABLE re.mapping_Size_Range AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Size_Range'] = c
        
    print('1.4 Size Range ',c,'筆')   
    cur.execute(sqlString)
    cur.execute('commit')
    conn = pymysql.connect(host=dbconfig.redb['host'], port=dbconfig.redb['port'],user=dbconfig.redb['user'], passwd=dbconfig.redb['passwd'], db=dbconfig.redb['db'])
    cur = conn.cursor()
    # 1.5 Defect Group
    c = 0
    sqlString = 'insert into re.mapping_Defect_Group(`group`,Defect_Group,creationdate)values'
    for index,row in data_xls[['組合','Defect Group']].iterrows():
        if row['組合'] != '':
            sqlString = sqlString+"('"+row['組合']+"','"+row['Defect Group']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_Defect_Group")
        #cur.execute("ALTER TABLE re.mapping_Defect_Group AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Defect_Group'] = c
        
    print('1.5 Defect Group ',c,'筆')
    cur.execute(sqlString)
    cur.execute('commit')
    # 1.6 Defect 不會用到的 Parts 
    c = 0
    sqlString = 'insert into re.mapping_Defect_no_Parts(Defect_Type,PART_NO,Parts_Type,creationdate)values'
    for index,row in data_xls[['Defect Type.1','PART_NO.1','Parts Type.1']].iterrows():
        if row['Defect Type.1'] != '':
            sqlString = sqlString+"('"+row['Defect Type.1']+"','"+str(row['PART_NO.1'])+"','"+row['Parts Type.1']+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_Defect_no_Parts")
        #cur.execute("ALTER TABLE re.mapping_Defect_no_Parts AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Defect_no_Parts'] = c
        
    print('1.6 Defect 不會用到的 Parts ',c,'筆')
    cur.execute(sqlString)
    cur.execute('commit')
    # sheet 2. Parts Cost ######################################################################################
    """
    data_xls = pd.read_excel(MappingFile, sheet_name='Parts Cost', header = 1).fillna('')
    c = 0
    sqlString = 'insert into re.mapping_Parts_Cost(ITEM_ID,USD,creationdate)values'
    for index,row in data_xls[['ITEM_ID','USD']].iterrows():
        if row['ITEM_ID'] != '':
            sqlString = sqlString+"('"+row['ITEM_ID']+"','"+str(row['USD'])+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("delete from re.mapping_Parts_Cost")
        cur.execute("ALTER TABLE re.mapping_Parts_Cost AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Parts_Cost'] = c
        
    print('2. Parts Cost ',c,'筆') 
    cur.execute(sqlString)
    """
    
    # sheet 4. Price ######################################################################################
    data_xls = pd.read_excel(xls, sheet_name='Price', header = 1).fillna('')
    # 4.1 mapping_Price_Normal
    c = 0
    sqlString = 'insert into re.mapping_Price_Normal(Model_Name,MID7,MID4,Prod_ID,Cust_Group,Normal,creationdate)values'
    for index,row in data_xls[['Model Name','MID 7','MID 4','Prod ID','Cust Group','Normal']].iterrows():
        if row['Normal'] != '':
            sqlString = sqlString+"('"+row['Model Name']+"','"+row['MID 7']+"','"+row['MID 4']+"','"+row['Prod ID']+"','"+row['Cust Group']+"','"+str(row['Normal'])+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :
        cur.execute("TRUNCATE re.mapping_Price_Normal")
        #cur.execute("ALTER TABLE re.mapping_Price_Normal AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Price_Normal'] = c
        
    print('4.1 mapping_Price_Normal ',c,'筆')    
    cur.execute(sqlString)
    cur.execute('commit')
    # 4.2 mapping_Price_DoS
    c = 0
    sqlString = 'insert into re.mapping_Price_DoS(Model_Name,MID7,MID4,Prod_ID,Cust_Group,DoS,creationdate)values'
    for index,row in data_xls[['Model Name.1','MID 7.1','MID 4.1','Prod ID.1','Cust Group.1','DoS']].iterrows():
        if row['DoS'] != '':
            sqlString = sqlString+"('"+row['Model Name.1']+"','"+row['MID 7.1']+"','"+row['MID 4.1']+"','"+row['Prod ID.1']+"','"+row['Cust Group.1']+"','"+str(row['DoS'])+"','"+creationdate+"'),"
            c = c + 1
    if c > 0 :        
        cur.execute("TRUNCATE re.mapping_Price_DoS")
        #cur.execute("ALTER TABLE re.mapping_Price_DoS AUTO_INCREMENT = 1")
        sqlString = sqlString[:-1]
        resultCount['mapping_Price_DoS'] = c
        
    print('4.2 mapping_Price_DoS ',c,'筆')    
    cur.execute(sqlString)
    cur.execute('commit')
    cur.close()
    conn.close()
    return resultCount
