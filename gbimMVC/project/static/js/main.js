
function page_router(page){
	if(page == 1){ //SMART FR 決策輔助
		window.location.replace("/gbim/smartfr");
		//$('#page_router').html('SMART FR 決策輔助')
	}else if(page == 2){ //全球不良品區域預測
		window.location.replace("/gbim/areaforecast");
		//$('#page_router').html('全球不良品區域預測')
	}else if(page == 3){ //全球備品庫存推薦
		window.location.replace("recommend");
		//$('#page_router').html('全球備品庫存推薦')
	}else if(page == 4){ //維修物料預警
		window.location.replace("alarm");
		//$('#page_router').html('維修物料預警')	
	}else if(page == 5){ //維修物料調撥推薦
		window.location.replace("safetystock");
		//$('#page_router').html('維修物料調撥推薦')
	}else if(page == 6){ //檢核機制
		window.location.replace("audit");
		//$('#page_router').html('檢核機制')
	}else if(page == 7){ //管理者功能
		window.location.replace("admin");
		//$('#page_router').html('管理者功能')
	}else if(page == 8){ //整機-備品-Forscast
		window.location.replace("set_forecast");
	}else if(page == 9){ //整機-備品-檢核
		window.location.replace("set_audit");
	}else if(page == 11){ //整機-備品-ftp報表
		window.location.replace("ftp_rpt");		
	}else if(page == 10){ //整機-物料
		window.location.replace("set_material");
	}else if(page == 20){ //CoPQ四大指標
		window.location.replace("indexes");
		//$('#page_router').html('整機')
	}   
}	

