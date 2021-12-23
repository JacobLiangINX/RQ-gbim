
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
	}else if(page == 4){ //維修中心庫存安全量
		window.location.replace("safetystock");
		//$('#page_router').html('維修中心庫存安全量')
	}else if(page == 5){ //檢核機制
		window.location.replace("audit");
		//$('#page_router').html('檢核機制')
	}else if(page == 6){ //管理者功能
		window.location.replace("admin");
		//$('#page_router').html('管理者功能')
	}
}	

