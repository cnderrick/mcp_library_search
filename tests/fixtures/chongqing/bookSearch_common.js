/*by seaou.com,qq:3026026;linzhaohai@hotmail.com*/
/** 兼容低版本，解决提交数组问题 */
jQuery.ajaxSettings.traditional = true;

function openUrl(url){

	var login_hid = document.getElementById("login_hid").value;
	var isLogin = false;
	if(login_hid!=null && login_hid!=undefined && login_hid!="" && login_hid!="undefined"){
		isLogin = true;
	} else {
		isLogin = false;
	}
	if (isLogin == true){
		window.open(url, "_blank");
	}else {
		alert("登录后可在线提交咨询，重庆图书馆地方文献室开放时间：星期二到星期六上午9点至下午5点，咨询电话：65210907")
	}
	
}

/**
 * 根据metas获取馆藏
 * @Param metas  metatable-metaid|metatable-metaid
 */
function getAsset(divId, metas){
	if ($('#'+divId).find("table").length > 0) {
		return;
	}

	var metatables = [];
	var metaids = [];

	var meta = metas.split('|');
	for (var i = 0; i < meta.length; i++) {
		metatables.push(meta[i].split('-')[0]);
		metaids.push(meta[i].split('-')[1]);
	}
	var positionIsShow = $('#positionIsShow').val();
	var collectionLocalShiftnoIsShow = $('#collectionLocalShiftnoIsShow').val();
	var localNotesIsShow = $('#localNotesIsShow').val();
	var params = {
		metatables: metatables,
		metaids: metaids,
		type: 'map',
		orderType:''
	}
	$.ajax({
		url: 'GetAsset.action',
		data: params,
		type: 'post',
		dataType: 'json',
		error: function() {
			alert("获取馆藏失败，请稍后再试！");
		},
		success: function(data) {
			var table = '<table>';
			table += '<tr><th >条码号</th><th >索书号</th><th >当前分馆</th><th >馆藏所在地点</th><th >状态</th><th >应还时间</th><th>备注</th><tr>';
			var map = data.map;
			var tempTr = '';
			var hasAsset = false;
			var subStr = ""
			$.each(map, function(key, value) {
				for (var i = 0; i < value.length; i++) {
					hasAsset = true;
					var asset = value[i];
					var retudate = "";
					if (asset.status.indexOf("借出") != -1) {
						retudate = asset.retudate;
						asset.status = '<span class="red">'+asset.status+'</span>';
					}
					var localCode = asset.curlocalCode && asset.curlocalCode.trim().length > 0 ? asset.curlocalCode : asset.localCode;
					var local = asset.curlocal && asset.curlocal.trim().length > 0 ? asset.curlocal : asset.local ;
					if(localNotesIsShow == '1'){
						subStr = '<div class="help-tip" var="'+localCode+'" onmouseover="getLocalNotes(this)"><p>馆藏详细信息加载中...</p></div>'
					}
					if (asset.status == '入藏') asset.status = '<span class="blue">在馆</span>';

					/*	var labelNote = getShelfLabelByBarcode(asset.barcode)
*/

					tempTr += "<tr sublib='"+asset.sublibCode+"' ><td>" + asset.barcode + "</td>" +
						"<td>" + asset.callno +"</td>" +
						"<td>" + asset.cursublib + "</td>" +
						"<td>" + local + subStr

					if ((local + subStr) == '重图地方文献'){
						var url = "http://ckzx.cqlib.cn/dfzx/front/?m=zx.dozx&tiaoma=" + asset.barcode + "&kahao=" + login_hid + "&title=" + document.querySelector('.list_item .info p').innerText.trim();
						tempTr += "<button id='openMessage' onclick=\"openUrl('" + url.replace(/'/g, "\\'") + "')\">咨询</button>";						}


					tempTr += "</td><td>" + asset.status+"</td>" +
						"<td>" + retudate+ "</td>" +
						/*		"<td>" + labelNote + "</td>" +*/
						"<td>" + asset.notes + "</td>" +
						"</tr>"
				}
			});
			if(!hasAsset){
				tempTr +="<tr><td colspan='7' style='text-align:center;'>无馆藏</td></tr>";
			}
			table += tempTr;
			table += "</table>"
			$('#'+divId).html(table);



			if(hasAsset && positionIsShow == '1'){
				position(divId);
			}

			if(hasAsset && collectionLocalShiftnoIsShow == '1'){
				collectionLocalShiftno(divId);
			}
			/**cdd*/
			/*if(data.basicSerialNumberIsShow == true){
                if(hasAsset && collectionLocalShiftnoIsShow == '1'){
                    collectionLocalShiftno(divId);
                }
            }*/

		}
	})
}



/**
 * 根据metas获取馆藏
 * @Param metas  metatable-metaid|metatable-metaid
 */
function getAssetByVolumeno(divId, volumeno){
	var flag=1;
	var positionIsShow = $('#positionIsShow').val();
	var localNotesIsShow = $('#localNotesIsShow').val();
	var params = {
		volumeno: volumeno,
		type: 'map',
		orderType:''
	}
	$.ajax({
		url: 'GetAsset.action',
		data: params,
		async: false,
		type: 'post',
		dataType: 'json',
		error: function() {
			alert("获取馆藏失败，请稍后再试！");
		},
		success: function(data) {
			var table = '<table>';
			if(divId=="toolTip"){
				table += '<tr><th >条码号</th><th >索书号</th><th >排架号</th><th >当前分馆</th><th >馆藏所在地点</th><th >状态</th><th >应还时间</th><th >层架信息</th><th >备注</th><tr>';
			}
			else
				table += '<tr><th >条码号</th><th >索书号</th><th >当前分馆</th><th >馆藏所在地点</th><th >状态</th><th >应还时间</th><th >层架信息</th><th >备注</th><tr>';
			var map = data.map;
			var tempTr = '';
			var hasAsset = false;
			var assetCount = 0;		//标记馆藏数量
			$.each(map, function(key, value) {
				for (var i = 0; i < value.length; i++) {
					hasAsset = true;
					var asset = value[i];
					var retudate = "";
					if (asset.status.indexOf("借出") != -1) {
						retudate = asset.retudate;
						asset.status = '<span class="red">'+asset.status+'</span>';
					}
					if (asset.status == '入藏') asset.status = '<span class="blue">在馆</span>';
					var labelNote = getShelfLabelByBarcode(asset.barcode)
					if(divId=="toolTip"){
						tempTr += "<tr><td>" + asset.barcode + "</td>" +
							"<td>" + asset.callno +"</td>" +
							"<td>" + asset.shiftno +"</td>" +
							"<td>" + asset.cursublib + "</td>" +
							"<td>" + asset.curlocal + "</td>" +
							"<td>" + asset.status+"</td>" +
							"<td>" + retudate+ "</td>" +
							"<td>" + labelNote + "</td>" +
							"<td>" + asset.notes + "</td>" +
							"</tr>"
					}
					else{
						tempTr += "<tr sublib='"+asset.sublibCode+"' ><td>" + asset.barcode + "</td>" +
							"<td>" + asset.callno +"</td>" +
							"<td>" + asset.cursublib + "</td>" +
							"<td>" + asset.curlocal + "</td>" +
							"<td>" + asset.status+"</td>" +
							"<td>" + labelNote + "</td>" +
							"<td>" + asset.notes + "</td>" +
							"</tr>"
					}
				}
				assetCount++;
			});
			if(!hasAsset){
				assetCount = 0;
				tempTr +="<tr><td colspan='7' style='text-align:center;'>无馆藏</td></tr>";
				flag=0;
			}
			table += tempTr;
			table += "</table>"
			$('#'+divId).html(table);
			if(hasAsset && positionIsShow == '1'){
				position(divId);
			}
		}
	})
	return flag;
}

/** 层架信息 */
function getShelfLabelByBarcode(barcode) {
	var note = "";
	var params = {
		barcode: barcode
	};
	$.ajax({
		url:'city/ShelfLabelAction.action',
		data: params,
		async: false,
		type: 'post',
		dataType: 'json',
		success: function(data) {
			var pos = data.shelfLabelNote == undefined ? "" : data.shelfLabelNote;
			note = pos;
		}
	});
	console.log("返回:"+note);
	return note;
}

/** 定位信息 */
function position(divId) {
	$("#"+divId+" table").each(function(i, table){
		$(table).find("th:last").after("<th>定位</th>");
		$(table).find("tr").each(function(i, tr){
			var barcode = $.trim($(tr).find("td:first").text());
			if(barcode=='') {
				$(tr).find("td:last").after("<td></td>");
				return;
			}

			var params = {
				barcode: barcode
			};
			$.ajax({
				//url: 'front/RFIDLocation.action',
				url:'city/PositionDetail.action',
				data: params,
				type: 'post',
				dataType: 'json',
				success: function(data) {
					var pos = data.location == undefined ? "" : data.location;
					//var location = data.location;
					//if (location != null && location != "null" && location != "") {
					//var href = "http://10.10.10.227/TSDW/GoToFlash.aspx?szbarcode=" + barcode;//吴忠馆
					//var href = "http://"+data.gpsIp + barcode;//海恒
					//$(tr).find("td:last").after("<td>"+"<a href='javascript:void(0);'  target='_blank' rel='noopener noreferrer' title='"+data.location == undefined ? '' : data.location+"'><font class='blue'>"+data.localtion== undefined ? '' : data.location+"</font></a>"+"</td>");
					$(tr).find("td:last").after("<td>"+"<a href='javascript:void(0);'  target='_blank' rel='noopener noreferrer' title='"+pos+"' ><font class='blue'>"+pos+"</font></a>"+"</td>");
					//}else{
					//$(tr).find("td:last").after("<td></td>");
					//}
				}
			});
		});

	})

}

/** 基藏流水号信息 */
function collectionLocalShiftno(divId) {

	$("#"+divId+" table").each(function(i, table){
		$(table).find("th").eq(1).after("<th>基藏流水号</th>");
		$(table).find("tr").each(function(i, tr){
			var sublib = $(tr).attr("sublib");
			var barcode = $.trim($(tr).find("td:first").text());
			if(barcode=='') {
				return;
			}
			var sublib;

			var params = {
				sublib: sublib,
				barcode: barcode
			};
			$.ajax({
				url: 'frontV2/CollectionLocalShiftno.action',
				data: params,
				type: 'post',
				dataType: 'json',
				success: function(data) {
					var shiftno = data.shiftno;
					if (shiftno != "null" && shiftno != null) {
						$(tr).find("td").eq(1).after("<td>"+shiftno+"</td>");
					}else{
						$(tr).find("td").eq(1).after("<td></td>");
					}
				}
			});
		});

	})

}

/** 获取书目详细信息 */
function getDetailed(divId, metatable, metaid){
	if ($('#'+divId).find("p").length > 0) {
		return;
	}
	var params = {
		metatable: metatable,
		id: metaid
	}
	$.ajax({
		url: 'frontV2/SearchBookDetail.action',
		data: params,
		type: 'post',
		dataType: 'json',
		error: function() {
			alert("获取详细信息失败，请稍后再试！");
		},
		success: function(data) {
			var marc = data.marcRecord;
			var title = encodeURIComponent(marc.fieldList['U_Title']);
			var gbktitle = data.gbktitle;
			var div = '';
			div += '<p><span>题名：</span>'+marc.fieldList['U_Title']+' </p>';
			div += '<p><span>作者：</span>'+marc.fieldList['U_Author']+' </p>';
			div += '<p><span>索书号：</span>'+marc.fieldList['U_Callno']+' </p>';
			div += '<p><span>出版项：</span>'+marc.fieldList['U_Publish']+'</p>';
			div += '<p><span>出版社：</span>'+marc.fieldList['U_Publish_Name']+'</p>';
			div += '<p><span>出版日期：</span>'+marc.fieldList['U_Publish_Time']+'</p>';
			div += '<p><span>分类号：</span>'+marc.fieldList['U_Classno']+'</p>';
			div += '<p><span>ISBN：</span>'+marc.fieldList['U_ISBN']+'</p>';
			div += '<p><span>价格：</span>'+marc.fieldList['U_Price']+'</p>';
			div += '<p><span>摘要：</span>'+marc.fieldList['U_Abstract']+'</p>';

			$('#'+divId).html(div);
		}
	})
}
/** 获取当前馆藏详细信息 */
function getLocalNotes(div){
	var localCode = $(div).attr("var");
	var text = $(div).text();
	var params = {
		localCode: localCode
	}

	if(text == '馆藏详细信息加载中...'){
		$.ajax({
			url: 'commonAjax/GetLocalNotes.action',
			data: params,
			async: false,
			type: 'post',
			dataType: 'json',
			error: function() {
				$(div).html("<p>获取馆藏详细信息失败，请稍后再试！</p>");
			},
			success: function(data) {
				if(data.localNotes != ''){
					$(div).html("<p>"+data.localNotes+"</p>");
				}else{
					$(div).html("<p>当前馆藏地点暂未设置详细描述</p>");
				}
			}
		});
	}
}

/** 获取期刊记到信息 */
function getChecked(divId, metatable, metaid){
	if ($('#'+divId).find("tr").length > 0) {
		return;
	}
	var params = {
		metatable: metatable,
		metaid: metaid
	}
	$.ajax({
		url: 'frontV2/SearchSeriesChecked.action',
		data: params,
		type: 'post',
		dataType: 'json',
		error: function() {
			alert("获取记到信息失败，请稍后再试！");
		},
		success: function(data) {
			var list = data.list;
			var table = '<table >';
			table += '<tr><th>记到年</th><th>分馆</th><th>卷</th><th>期</th><th>总期号</th><th>应到日期</th><th>到馆日期</th><th>复本数</th><th>记到分配信息</th><tr>';
			var tempTr = '';
			for(var i=0;i<list.length;i++){
				var map=new ByteMap();
				var tempMap=list[i];
				$.each(tempMap,function(key,value){
					map.put(key,value);
				});
				tempTr+="<tr>";
				tempTr += "<td >" + map.get("acqyear")  + "</td>" ;
				tempTr += "<td >" + map.get("sublib") + "</td>" ;
				tempTr += "<td >" + map.get("volVolume")  + "</td>" ;
				tempTr += "<td >" + map.get("period")  + "</td>" ;
				tempTr += "<td >" + map.get("volTolvol")  + "</td>" ;
				tempTr += "<td >" + map.get("volPubdate") + "</td>" ;
				tempTr += "<td >" + map.get("updateDate") + "</td>" ;
				tempTr += "<td >" + map.get("acqCopys") + "</td>" ;
				tempTr += "<td id='checkId'>" + "<a  index="+i+ " style='cursor:pointer' onmouseover='showToolTip(this,event);' onmouseout='ToolTip.HideTip(this);' volumeno="+map.get("volumeno")+">"+map.get("local")+ "</a>"+"</td>" ;
				tempTr+="<tr>";
			}
			if(list.length<=0){
				tempTr +="<tr><td colspan='6' style='text-align:center;'>无记到信息</td></tr>";
			}
			table+=tempTr;
			table += "</tr></table>"
			$('#'+divId).html(table);

		}
	})
}
/** 获取期刊记到信息 */
function getChecked(divId, metas){
	if ($('#'+divId).find("table").length > 0) {
		return;
	}

	var metatables = [];
	var metaids = [];

	var meta = metas.split('|');
	for (var i = 0; i < meta.length; i++) {
		metatables.push(meta[i].split('-')[0]);
		metaids.push(meta[i].split('-')[1]);
	}
	var params = {
		metatables: metatables,
		metaids: metaids
	}
	$.ajax({
		url: 'frontV2/SearchSeriesChecked.action',
		data: params,
		type: 'post',
		dataType: 'json',
		error: function() {
			alert("获取记到信息失败，请稍后再试！");
		},
		success: function(data) {
			var list = data.list;
			var table = '<table >';
			table += '<tr><th>记到年</th><th>分馆</th><th>卷</th><th>期</th><th>总期号</th><th>应到日期</th><th>到馆日期</th><th>复本数</th><th>记到分配信息</th><tr>';
			var tempTr = '';
			for(var i=0;i<list.length;i++){
				var map=new ByteMap();
				var tempMap=list[i];
				$.each(tempMap,function(key,value){
					map.put(key,value);
				});
				tempTr+="<tr>";
				tempTr += "<td >" + map.get("acqyear")  + "</td>" ;
				tempTr += "<td >" + map.get("sublib") + "</td>" ;
				tempTr += "<td >" + map.get("volVolume")  + "</td>" ;
				tempTr += "<td >" + map.get("period")  + "</td>" ;
				tempTr += "<td >" + map.get("volTolvol")  + "</td>" ;
				tempTr += "<td >" + map.get("volPubdate") + "</td>" ;
				tempTr += "<td >" + map.get("updateDate") + "</td>" ;
				tempTr += "<td >" + map.get("acqCopys") + "</td>" ;
				tempTr += "<td id='checkId'>" + "<a  index="+i+ " style='cursor:pointer' onmouseover='showToolTip(this,event);' onmouseout='ToolTip.HideTip(this);' volumeno="+map.get("volumeno")+">"+map.get("local")+ "</a>"+"</td>" ;
				tempTr+="<tr>";
			}
			if(list.length<=0){
				tempTr +="<tr><td colspan='9' style='text-align:center;'>无记到信息</td></tr>";
			}
			table+=tempTr;
			table += "</tr></table>"
			$('#'+divId).html(table);

		}
	})
}
function showToolTip(obj, e) {
	var tipPanel = document.getElementById("tipPanel" + $(obj).attr("index"));
	if (tipPanel != null) {
		ToolTip.Init(obj,e);
	} else {
		var volumenoValue = $(obj).attr("volumeno");
		var flag = getAssetByVolumeno("toolTip", volumenoValue);
		if (flag == 1) {
			ToolTip.Init(obj,e);
		}
	}
}


/** 收藏 */
function collect(isLogin,metatable,metaid){
	if(isLogin!='true'){
		alert('您还未登录，不能收藏！');
	} else {
		var params = {
			metatable: metatable,
			metaid: metaid
		}
		$.ajax({
			url: 'frontV2/CollectionAction.action',
			data: params,
			type: 'post',
			dataType: 'json',
			error: function() {
				alert("收藏失败，请稍后再试！");
			},
			success: function(data) {
				alert(data.msg);
			}
		});

	}
}



