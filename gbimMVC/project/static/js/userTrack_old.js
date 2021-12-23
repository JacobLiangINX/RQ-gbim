//== 這段貼在各前端網頁 ========================================================================
/*
// <script src="../static/js/3.1.1/jquery.js"></script> // 前提條件，需有jquery，版本不限。 
// <script src="../static/js/userTrack.js"></script>  // 引用本js lib檔
$(document).ready(function() {  
	userTrackConfig.serviceKey = 111111;
	userTrackConfig.PERNR = 18017220 // 工號:在login前為空，login前不用設定，login後才需給定。

	// 依需求log user的操作，例如 : 登入index/查詢.../上下載.../
	// 滑鼠停止與重整，工程師不需要編碼紀錄，本lib已有紀錄。
	saveEventLog('login page');
	saveEventLog('index page');
	saveEventLog('{action:query,fromYM:202010,toTM:202106}');	
	logReloadOrCloseBrowser(); // 紀錄關閉瀏覽器的動作 
});
*/
//== user Track lib ==========================================================================

var userTrackConfig = {
	ajaxUrlPort : '10.55.23.168:34081', // userTrack Server API
	serviceKey : '',              // 每個服務所申請的key
	PERNR : '',                   // 工號:在login前為空，login後需給定。
	saveMainLogFrequency : 10000, // Log回存userTrack Server頻率，頻率太高會影響Client效能，建議:30秒(單位:毫秒，1000毫秒=1秒)。
	ip : '',                      // 取得客端IP(需連外，海外/Citrix/機房Server => fail)
	eventList : [],               // 事件集暫存
	deBug : false                 // console.log會出現紀錄 
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
			  alert('mainLog Ajax request 發生錯誤:'+JSON.stringify(xhr));
			}
		}); 			 
	}
}

// 取得客端IP(需連外，海外/Citrix/機房Server => fail)
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

// 滑鼠靜止偵測 
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

// 重整或關閉視窗偵測
function logReloadOrCloseBrowser(){
	window.addEventListener('beforeunload', function (e) { 
		e.preventDefault();
		saveEventLog('reloadOrClose')
		saveMainLog()
		e.returnValue = '';	
	});
}
// 取得client日期時間
function getFormattedDate() {
    var date = new Date();
    var str = date.getFullYear() + "/" + (date.getMonth() + 1) + "/" + date.getDate() + " " +  date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds();
    return str;
}