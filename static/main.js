// custom javascript

$(document).ready(function () {
    console.log('ok!');

    var now = new Date();
    var yesterday = new Date();
    yesterday.setDate(now.getDate() - 1);

    var orderDownloadDatePicker = $('#orderDownloadDate');
    orderDownloadDatePicker.datepicker({
        minView: "day", //  选择时间时，最小可以选择到那层；默认是‘hour’也可用0表示
        language: "zh-CN", // 语言
        autoclose: true, //  true:选择时间后窗口自动关闭
        format: 'yyyy-mm-dd', // 文本框时间格式，设置为0,最后时间格式为2017-03-23 17:00:00
        todayBtn: "linked", // 如果此值为true 或 "linked"，则在日期时间选择器组件的底部显示一个 "Today" 按钮用以选择当前日期。
        endDate: now, // 窗口可选时间从今天开始
        orientation: "bottom",    //方向
        todayHighlight: true,
        weekStart: 0
    });

    // if (orderDownloadDatePicker.val()) {
    //     orderDownloadDatePicker.datepicker("setDate", yesterday);
    // }

});

function getSessionId() {
    return $("#sessionId").val();
}

function getOrderDownloadDate() {
    return $("#orderDate").val();
}

function loadMerchantInfo() {
    var sessionId = getSessionId();
    console.log("sessionId=" + sessionId);
    $.ajax({
        type: 'POST',
        url: '/merchant_info',
        data: {
            sessionId: sessionId
        },
        success: onLoadMerchantInfoSuccess(),
        fail: onLoadMerchantInfoFail()
    })
}

function onLoadMerchantInfoSuccess(res) {
    console.log("load merchant info successfully:" + res);
}

function onLoadMerchantInfoFail(res) {
    console.warn("load merchant info failed:");
}

function downloadOrders() {
    var orderDate = getOrderDownloadDate();
    console.log("orderDate=" + orderDate);
}

