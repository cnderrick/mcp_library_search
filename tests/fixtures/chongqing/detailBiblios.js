/*by seaou.com,qq:3026026;linzhaohai@hotmail.com*/


/** 预约 */
function reserve(){
	var noteType = $('#noteType').val();
	var libMetas = $('#libMetas').val();
	var params = {
			noteType: noteType,
			libMetas: libMetas
	    }
	$.ajax({
        url: 'frontV2/Reserve!request.action',
        data: params,
        type: 'post',
        dataType: 'json',
        error: function() {
            alert("预约失败，请稍后再试！");
        },
          success:function(data){
			var flag = data.flag;
			var message = data.message;
			if(flag == false){ // 未登录
				requestFlag = 'login';
				$('#requestDIV').html('<br>'+'<span id="message" style="color:red;align:center"><strong>'+message+'</strong></span><br>'+'<div class="table_list"><table><tr width="100%"><td height="25"  width="40%" align="right" bgcolor="#eef6fd">登录名：<span style="color: red;">*</span></td><td height="25" align="left"><input type="text" style="width:96%" id="readerName" name="readerName"/></td></tr><tr><td height="25"  align="right" bgcolor="#eef6fd">密码：<span style="color: red;">*</span></td><td height="25" width="220" align="left"><input style="width:96%" type="password" id="password"  name="password"  onkeydown="if(event.keyCode==13) frontLogin()"/></td></tr></table></div>');
			}else{
				requestFlag = 'close';
				$('#requestDIV').html("<br><br><div id='message' align='center' style='color:red'><strong>"+message+"</strong></div>");
			}
			$("#requestDIV").dialog('open');
   		}
	})
}

// 登录
function frontLogin(){
	$('#message').remove();
	var  readerName=$.trim($("input[name=readerName]").val());
	var password=$.trim($("input[name=password]").val());
	if(readerName=="" ){
		alert("登录名不能为空！");
		$('#readerName').focus();
	}else if(password=="" ){
		alert("密码不能为空！");
		$('#password').focus();
	}else{
		$.ajax({
			url:'FrontLogin!loginAjax.action',
			data : { readerName : readerName, password : password, type:'reserveReg'} ,
	   		type: 'post',
	   		dataType:'json',
			error:function(){
				alert("系统出错登录失败，请联系管理员！");
			},
	   		success:function(data){
				var flag = data.flag;
				var tag = data.tag;
				var message = data.message;
				if(flag == true){
					requestFlag = 'request';
					reserve();
				}else{
					$('#requestDIV').append("<div id='message' style='color:red'><strong>"+message+"</strong></div>");
				}
	   		}
		});
	}
}

var pageNo=1;
function getComment(divId,metatable,metaid){
	 var params={
			 currentPage: pageNo,
			 title: metatable,
		     id: metaid	
	}
	$.ajax({
        url: 'frontV2/ReaderRecommend!readerPL.action',
        data: params,
        type: 'post',
        dataType: 'json',
        error: function() {
            alert("获取评论信息失败，请稍后再试！");
        },
        success: function(data) {	
        	  var tempTr = '';     		
        	  var map = data.map;
        	  if(map.list.length!=0){
	              for (var i in map.list) {
	                  var a = map.list[i].score;
	                  var name = map.list[i].name;
	                  var createdate = map.list[i].createdate;
	                  var createtime = map.list[i].createtime;
	                  var notes = map.list[i].notes;
	                  var b = "";
	                  var k = 0;
	                  for (var i = 0; i < a; i++) {
	                      b = b + "★";
	                      k++;
	                  }
	                  tempTr+='<a href="javascript:void(0);" onclick="historyRecPage(\'pre\',\''+divId+'\',\''+metatable+'\',\''+metaid+'\');">上一页</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="javascript:void(0);" onclick="historyRecPage(\'next\',\''+divId+'\',\''+metatable+'\',\''+metaid+'\');">下一页</a><div class="review"><h4><span>'+name+'<em>('+createdate+'   '+createtime+')</em></span></h4>'+'<font color="#FBA994">' + b + '(' + k + '颗星)<font>'+'<p>'+notes+'</p></div>';
	              }   	
        	  }else{
        		  if(pageNo>1){
        			  historyRecPage('pre',divId, metatable,metaid);
        			  return;
        		  }
                  tempTr+='<div class="review" style="text-align:center"><span >还没有评论，赶快去评论说出你的感受吧！</span></div>';
        	  }
            $('#'+divId).html(tempTr);
        }
    })
	
}

function historyRecPage(msg, divId, metatable, metaid){
	if(msg=="pre"){
		pageNo--;
		if(pageNo<1) pageNo=1;
	} else {
		pageNo++;
	}
	getComment(divId,metatable,metaid);
}
function ifLogin() {
    var b = false;
    $.ajax({
        url: 'ReserveRegAjax!find.action',
        type: 'post',
        dataType: 'json',
        async: false,
        error: function() {
            alert("系统出错判断用户是否登录出错，请联系管理员！");
            return false;
        },
        success: function(data) {
            var flag = data.flag;
            b = flag;
        }
    });
    return b;
}

function checkValue(mess, start) {
    if (mess == "") {
        alert("请填写评论内容");
        $("#textarea_ly").focus();
        return false;
    }
    if (start == "") {
        alert("请填选择星级");
        return false;
    }
    return true;
}
function redstart(sid) {
    $("#strat_tj>label").each(function(i, la) {
        var id = $(la).attr("id") * 1;
        if (sid >= id) $(la).html("★");
        else $(la).html("☆");
    });
    $("#in_start").val(sid);
}
function bindLable(){
	$("#strat_tj>label").bind("click",function(){redstart(this.id,true);});
	$("#strat_tj>label").css({color:'#FBA994'});
}
function sub_pl(metatable, metaid) {
	if (!ifLogin()) {	
        $("#log_div").show();
        $("input[name=uname]").focus();
        return;
    }
	 var mess = $.trim($("#textarea_ly").val());
	 var start = $.trim($("#in_start").val());
	 if (!checkValue(mess, start)) return;
    var url = "frontV2/ReaderRecommend!verifyTwo.action";
    $.getJSON(url, {
        metaid: metaid,
        metatable: metatable
    },
    function(data) {
        if (data.total * 1 > 0) {
        	alert("你已评论过此书");
        	 $("#textarea_ly").html("");
             $("#strat_tj>label").each(function(i, la) {
                 $(la).html("☆");
             });
        	}
        else {
            var url = "frontV2/ReaderRecommend!down.action";
            $.post(url, {
                notes: mess,
                id: metaid,
                metatable: metatable,
                score: start,
                status:'C1'
            },
            function(data) {
              alert("评论成功");
              $("#textarea_ly").html("");
              $("#strat_tj>label").each(function(i, la) {
                  $(la).html("☆");
              });
            });
        }

    });
}
function showlogin() {
    $("input[name=uname]").focus();
    $("#log_div").show();
}
function hidelogin() {
    $("#log_div").hide();
}
function usrlogin() {
    var uname = $.trim($("input[name=uname]").val());
    var upwd = $.trim($("input[name=upwd]").val());
    var authcode = $.trim($("input[name=authcode]").val());
    if (uname == "") {
        alert("请输入用户名");
        $("input[name=uname]").focus();
        return;
    }
    if (upwd == "") {
        alert("请输入密码");
        $("input[name=upwd]").focus();
        return;
    }
    if (authcode == "") {
        alert("请输入验证码");
        $("input[name=upwd]").focus();
        return;
    }
    $.ajax({
        url: 'FrontLogin!loginCodeAjax.action',
        data: {
            readerName: uname,
            password: upwd,
            type: 'reserveReg',
            imgcode: authcode
        },
        type: 'post',
        dataType: 'json',
        error: function() {
            alert("系统出错登录失败，请联系管理员！");
        },
        success: function(data) {
            var flag = data.flag;
            var tag = data.tag;
            var message = data.message;
            if (flag == true) {
                $("#login_div").hide();
                $("#log_div").hide();
                $("[name=login_dis]").attr({
                    disabled: false
                });
                $("#textarea_ly").attr({
                    readonly: false
                });
                $("#textarea_ly").focus();
            } else {
                alert(data.message);
            }
        }
    });
}

function postToWb() {
    var imgurl = "";
    $("#ct_table img").each(function(i, img) {
        imgurl += $(img).attr("src") + ",";
    });
    var _t = encodeURI(document.title);
    var _url = encodeURIComponent(document.location);
    var _appkey = encodeURI("appkey");
    var _pic = encodeURI(imgurl);
    var _site = "";
    var _u = 'http://v.t.qq.com/share/share.php?title=' + _t + '&url=' + _url + '&appkey=' + _appkey + '&site=' + _site + '&pic=' + _pic;
    window.open(_u, '分享到腾讯微博', 'width=700, height=680, top=0, left=0, toolbar=no, menubar=no, scrollbars=no, location=yes, resizable=no, status=no');
}
$(function(){
	$('a[name="volumenoli"]').click(function(){
		var volumeno = $(this).attr('volumeno');
		getAssetByVolumeno('seriesAssetID', volumeno);
	})
})

//////////////////////////////////
$(function(){
				$('body').append('<div id="requestDIV"  style="text-align:center"></div>');
				$('#requestDIV').dialog({
					bgiframe:true,
					title:'申请预约',
					autoOpen:false,
					width:400,
					height:225,
					position:'center',
					modal:true,
					draggable:false,
					buttons:{
						'取消':function(){
								$('#message').remove();
								$(this).dialog('close');
							},
						'确定':function(){
								$('#message').remove();
								if(requestFlag == 'login'){
									frontLogin();
								}else if(requestFlag == 'request'){
									request();
								}else if(requestFlag == 'close'){
									$('#requestDIV').dialog('close');
								}
							}
					}
				});
			})
$(function() {
    var tabcon = $('.tabs_box .tabs_con');
    tabcon.hide();

    // 馆藏信息，详细信息，等
    $('.tabs_box > ul > li a').click(function() {
        tabcon.slideUp(200);
        $('.tabs_box ul li a').removeClass('current');
        /*$(this).parents('.tabs_box').find('.tabs_con').slideUp(300);*/
        $(this).parents('.tabs_box').find('.tabs_con').filter(this.hash).slideDown(300);
        $(this).parents('ul').find('a').removeClass('current');
        $(this).addClass('current');
        if($(this).attr('id')=='getCommoned'){
        	var divId = $(this).attr('index');
        	var metatable = $(this).attr('metatable');
       	   	var metaid = $(this).attr('metaid');
       	   	pageNo=1;
        	getComment(divId,metatable, metaid);
        }
        return false;
    }).filter(':first').click(); // 控制馆藏载入显示
});

$(function() {
    bindLable();
	// 馆藏信息 显示分馆
    $('.list_sub_tabs ul li a').click(function() {
        $(this).parents('.list_sub_tabs').find('.sub_con').hide();
        $(this).parents('.list_sub_tabs').find('.sub_con').filter(this.hash).fadeIn(400).show();
        $(this).parents('ul').find('a').removeClass('current1');
        $(this).addClass('current1');
        var divId = $(this).attr('aId');
        var metas = $(this).attr('metas');
        getAsset(divId, metas);
        return false;
    }).filter('.first').click();
    $('.list_sub_tabs_check ul li a').click(function() {
        $(this).parents('.list_sub_tabs_check').find('.sub_con').hide();
        $(this).parents('.list_sub_tabs_check').find('.sub_con').filter(this.hash).fadeIn(400).show();
        $(this).parents('ul').find('a').removeClass('current1');
        $(this).addClass('current1');
        var divId = $(this).attr('aId');
        var metas = $(this).attr('metas');
        getChecked(divId, metas);
        return false;
    }).filter('.second').click();
});

$(function() {
    var Accordion = $('#search_option');
    Accordion.switchable({
        triggers: $('.option_title'),
        triggerType: 'click',
        panels: '.option_con',
        effect: 'accordion',
        multiple: true,
        initIndex: 0 // new value only for accordion
    });


    var Accordion = $('.zine_date');
    Accordion.switchable({
        triggers: $('.title'),
        triggerType: 'click',
        panels: 'dl',
        effect: 'accordion',
        multiple: true,
        initIndex: 0 // new value only for accordion
    });
});