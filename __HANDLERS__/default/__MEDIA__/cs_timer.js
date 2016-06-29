// This file is part of CAT-SOOP
// Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
// CAT-SOOP is free software, licensed under the terms described in the LICENSE
// file.  If you did not receive a copy of this file with CAT-SOOP, please see:
// https://cat-soop.org/LICENSE

$('body').append('<div id="timer" class="response" style="position:fixed;right:10px;bottom:0px;width:auto;z-index:10000;"></div><p>');

$(document).ready(function(){
    var cs_timer_remaining = cs_timer_due-cs_timer_now;
    cs_timer_timer();
    var cs_timer_counter = setInterval(cs_timer_timer,1000);
    function cs_timer_timer() {
        cs_timer_remaining=cs_timer_remaining-1;
        if(cs_timer_remaining <= 0){
            clearInterval(cs_timer_counter);
            cs_ajaxrequest(cs_all_questions,'lock');
        }else{
            if (cs_timer_remaining%20 == 0){
                setTimeout(function(){
                               $.ajax(cs_time_url).done(function(mmsg){
                                                            cs_timer_remaining = cs_timer_due - parseInt(mmsg);
                                                        });
                           }, Math.floor((Math.random() * 2000) + 1000));
            }
            cs_timer_hours = Math.floor(cs_timer_remaining / 3600);
            cs_timer_minutes = Math.floor((cs_timer_remaining - (cs_timer_hours*3600)) / 60);
            cs_timer_seconds = cs_timer_remaining - (cs_timer_hours*3600) - (cs_timer_minutes*60);
            $('#timer').html('Time Remaining: ');
            $('#timer').append('' + cs_timer_hours + ' hours, ' + cs_timer_minutes + ' minutes, ' + cs_timer_seconds + ' seconds');
        }
    }
});
