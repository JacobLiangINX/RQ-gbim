//== �o�q�K�b�U�e�ݺ��� ========================================================================
/*
// <script src="../static/js/3.1.1/jquery.js"></script> // �e������A�ݦ�jquery�A���������C 
// <script src="../static/js/userTrack.js"></script>  // �ޥΥ�js lib��
$(document).ready(function() {  
	userTrackConfig.serviceKey = 111111;
	userTrackConfig.PERNR = 18017220 // �u��:�blogin�e���šAlogin�e���γ]�w�Alogin��~�ݵ��w�C

	// �̻ݨDlog user���ާ@�A�Ҧp : �n�Jindex/�d��.../�W�U��.../
	// �ƹ�����P����A�u�{�v���ݭn�s�X�����A��lib�w�������C
	saveEventLog('login page');
	saveEventLog('index page');
	saveEventLog('{action:query,fromYM:202010,toTM:202106}');	
	logReloadOrCloseBrowser(); // ���������s�������ʧ@ 
});
*/
//== user Track lib ==========================================================================

var userTrackConfig = {
	//ajaxUrlPort : '10.55.23.168:34081', // userTrack Server API
	ajaxUrlPort : 'tnvppynsrv2/usertrackapi', // userTrack Server API
	serviceKey : '',              // �C�ӪA�ȩҥӽЪ�key
	PERNR : '',                   // �u��:�blogin�e���šAlogin��ݵ��w�C
	saveMainLogFrequency : 10000, // Log�^�suserTrack Server�W�v�A�W�v�Ӱ��|�v�TClient�į�A��ĳ:30��(���:�@��A1000�@��=1��)�C
	ip : '',                      // ���o�Ⱥ�IP(�ݳs�~�A���~/Citrix/����Server => fail)
	eventList : [],               // �ƥ󶰼Ȧs
	deBug : false                 // console.log�|�X�{���� 
}

$(function() {
	ipLookUp();
	setInterval("saveMainLog();", userTrackConfig.saveMainLogFrequency);
});
 
function saveEventLog(event){
	if(userTrackConfig.deBug) console.log('saveEventLog: '+event);
	eventObj = {}; 
	eventObj["event"] = event;
	eventObj["creationdate"] = getFormattedDate();//new Date().toLocaleString({timeZone: "Asia/Taipei"}) //Math.round(new Date().getTime()/1000);		
	userTrackConfig.eventList.push(eventObj);
} 

function saveMainLog(){ 
	if(userTrackConfig.deBug) console.log('saveMainLog: '+userTrackConfig.eventList);
	if(userTrackConfig.eventList.length > 0){	
		 
		$.ajax({  	
			url: "http://"+userTrackConfig.ajaxUrlPort+"/userTrackLog",	
			type: "GET",
			dataType: 'json',
			data:  {
				serviceKey : userTrackConfig.serviceKey,
				url : window.location.href,
				PERNR : userTrackConfig.PERNR,
				ip : userTrackConfig.ip, 
				userTrackEventList : JSON.stringify(userTrackConfig.eventList)} ,
				
			contentType: "application/json; charset=utf-8",
			traditional: true,
			success: function (data) {  
				 userTrackConfig.eventList = [];				  
			},				
			error: function(xhr) {
			  alert('mainLog Ajax request �o�Ϳ��~:'+JSON.stringify(xhr));
			}
		}); 			 
	}
}

// ���o�Ⱥ�IP(�ݳs�~�A���~/Citrix/����Server => fail)
function ipLookUp () {
  $.ajax('http://ip-api.com/json')
  .then(
      function success(response) { 
		  userTrackConfig.ip = response.query	 
      },
      function fail(data, status) {		  
		  userTrackConfig.ip = 'fail' 
      }
  );
}

// �ƹ��R��� 
(function(){ 
    let isMove = false,
    timer = null;
    window.onmousemove = function(){
        isMove = true;
        clearTimeout(timer); 
		timer = setInterval(function(){	
            isMove = false; 
			saveEventLog('mouseIdle30s') 
        },30000);
    }
}());

// �����������������
function logReloadOrCloseBrowser(){
	window.addEventListener('beforeunload', function (e) { 
		e.preventDefault();
		saveEventLog('reloadOrClose')
		saveMainLog()
		e.returnValue = '';	
	});
}
// ���oclient����ɶ�
function getFormattedDate() {
    var date = new Date();
    var str = date.getFullYear() + "/" + (date.getMonth() + 1) + "/" + date.getDate() + " " +  date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds();
    return str;
}