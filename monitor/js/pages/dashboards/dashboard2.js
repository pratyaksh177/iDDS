/*
Template Name: Admin Pro Admin
Author: Wrappixel
Email: niravjoshi87@gmail.com
File: js
*/
$(function () {
    "use strict";
    // ============================================================== 
    // Newsletter
    // ============================================================== 

    function draw_chartist(group_types, group_types_name, chartist_name, labels, num_monthly) {
        $.each(group_types, function(i) {
            var new_li = '<li class="ps-3"><h5><i class="fa fa-circle me-1 ';
            new_li += 'view_chartist_lable_' + i + '"></i>' + group_types[i]+ '</h5>';
            new_li += '</li>';
            $(group_types_name).append(new_li);
        });

        new Chartist.Line(chartist_name, {
            labels: labels,
            series: num_monthly
            },
            {top: 0,
             low: 1,
             showPoint: true,
             fullWidth: true,
             plugins: [
                 Chartist.plugins.tooltip()
             ],
            axisY: {
                labelInterpolationFnc: function (value) {
                    // return (value / 1) + 'k';
                    return value;
                }
            },
            showArea: false
        });
    }

    function draw_chartist_status(data) {

        // alert(Object.keys(data.month_acc_status.Total));
        var labels = Object.keys(data.month_acc_status.Total);
        var statuses = Object.keys(data.month_acc_status);
        var num_monthly = Object.keys(data.month_acc_status).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_status[key]).map(function(key1){
                return data.month_acc_status[key][key1];
            });
            return mnum_monthly_status;
        });

        draw_chartist(statuses, '#view_chartist_labels_status', '#view_chartist_status', labels, num_monthly);
    }

    function draw_chartist_files(data) {

        var labels = Object.keys(data.month_acc_processed_files.Total);
        var statuses = Object.keys(data.month_acc_processed_files);
        var num_monthly = Object.keys(data.month_acc_processed_files).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_processed_files[key]).map(function(key1){
                return Math.round(data.month_acc_processed_files[key][key1]/1000);
                // return data.month_acc_processed_files[key][key1];
            });
            return mnum_monthly_status;
        });

        draw_chartist(statuses, '#view_chartist_labels_files', '#view_chartist_files', labels, num_monthly);
    }

    function draw_chartist_bytes(data) {

        // alert(Object.keys(data.month_acc_status.Total));
        var labels = Object.keys(data.month_acc_processed_bytes.Total);
        var statuses = Object.keys(data.month_acc_processed_bytes);
        var num_monthly = Object.keys(data.month_acc_processed_bytes).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_processed_bytes[key]).map(function(key1){
                var n_value = data.month_acc_processed_bytes[key][key1];
                n_value = Math.round(n_value/1000/1000/1000/1000);
                return n_value;
            });
            return mnum_monthly_status;
        });

        draw_chartist(statuses, '#view_chartist_labels_bytes', '#view_chartist_bytes', labels, num_monthly);
    }

    function draw_chartist_status_type(data) {

        var labels = Object.keys(data.month_acc_status.Total);
        var g_types = Object.keys(data.month_acc_status_dict_by_type);
        var num_monthly = Object.keys(data.month_acc_status_dict_by_type).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_status_dict_by_type[key].Total).map(function(key1){
                return data.month_acc_status_dict_by_type[key].Total[key1];
            });
            return mnum_monthly_status;
        });

        draw_chartist(g_types, '#view_chartist_labels_type', '#view_chartist_type', labels, num_monthly);
    }

    function draw_chartist_files_type(data) {

        var labels = Object.keys(data.month_acc_status.Total);
        var g_types = Object.keys(data.month_acc_processed_files_by_type);
        var num_monthly = Object.keys(data.month_acc_processed_files_by_type).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_processed_files_by_type[key].Total).map(function(key1){
                return data.month_acc_processed_files_by_type[key].Total[key1];
            });
            return mnum_monthly_status;
        });

        draw_chartist(g_types, '#view_chartist_labels_files_type', '#view_chartist_files_type', labels, num_monthly);
    }

    function draw_chartist_bytes_type(data) {

        var labels = Object.keys(data.month_acc_status.Total);
        var g_types = Object.keys(data.month_acc_processed_bytes_by_type);
        var num_monthly = Object.keys(data.month_acc_processed_bytes_by_type).map(function(key){
            var mnum_monthly_status = Object.keys(data.month_acc_processed_bytes_by_type[key].Total).map(function(key1){
                return Math.round(data.month_acc_processed_bytes_by_type[key].Total[key1]/1000/1000/1000/1000);
            });
            return mnum_monthly_status;
        });

        draw_chartist(g_types, '#view_chartist_labels_bytes_type', '#view_chartist_bytes_type', labels, num_monthly);
    }


    var sparklineLogin = function () {
        var iddsAPI_request = appConfig.iddsAPI_request;
        var iddsAPI_transform = appConfig.iddsAPI_transform;
        var iddsAPI_processing = appConfig.iddsAPI_processing;

        $.getJSON(iddsAPI_transform, function(data){ 
            $('#totaltransforms span').text(data.total);
            var month_transforms = Object.keys(data.month_status.Total).map(function(key){
                return data.month_status.Total[key];
            });
            $('#totaltransformslinedash').sparkline(month_transforms, {
                type: 'bar',
                height: '30',
                barWidth: '4',
                resize: true,
                barSpacing: '5',
                barColor: '#7460ee'
            });

            $('#totalfiles span').text(data.total_files);
            var month_files = Object.keys(data.month_processed_files.Total).map(function(key){
                return data.month_processed_files.Total[key];
            });
            $('#totalfileslinedash').sparkline(month_files, {
                type: 'bar',
                height: '30',
                barWidth: '4',
                resize: true,
                barSpacing: '5',
                barColor: '#7460ee'
            });

            $('#totalbytes span').text(Math.round(data.total_bytes/1000/1000/1000/1000));
            var month_bytes = Object.keys(data.month_processed_bytes.Total).map(function(key){
                return data.month_processed_bytes.Total[key];
            });
            $('#totalbyteslinedash').sparkline(month_bytes, {
                type: 'bar',
                height: '30',
                barWidth: '4',
                resize: true,
                barSpacing: '5',
                barColor: '#7460ee'
            });

            draw_chartist_status(data);
            draw_chartist_files(data);
            draw_chartist_bytes(data);
            draw_chartist_status_type(data);
            draw_chartist_files_type(data);
            draw_chartist_bytes_type(data);
        });

    }

    var sparkResize;
    $(window).on("resize", function (e) {
        clearTimeout(sparkResize);
        sparkResize = setTimeout(sparklineLogin, 500);
    });
    sparklineLogin();

});


