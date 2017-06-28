/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the Soopycat License, version 2.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.
 *
 * You should have received a copy of the Soopycat License along with this
 * program.  If not, see <https://smatz.net/soopycat>.
 */

$('body').append('<div id="timer" class="response" style="position:fixed;right:10px;bottom:0px;width:auto;z-index:10000;"></div><p>');

$(document).ready(function(){
    catsoop.timer_remaining = catsoop.timer_due-catsoop.timer_now;
    catsoop.timer = function () {
        catsoop.timer_remaining=catsoop.timer_remaining-1;
        if(catsoop.timer_remaining <= 0){
            clearInterval(catsoop.timer_counter);
            catsoop.ajaxrequest(catsoop.all_questions,'lock');
        }else{
            if (catsoop.timer_remaining%20 == 0){
                setTimeout(function(){
                               $.ajax(catsoop.time_url).done(function(mmsg){
                                                            catsoop.timer_remaining = catsoop.timer_due - parseInt(mmsg);
                                                        });
                           }, Math.floor((Math.random() * 2000) + 1000));
            }
            catsoop.timer_hours = Math.floor(catsoop.timer_remaining / 3600);
            catsoop.timer_minutes = Math.floor((catsoop.timer_remaining - (catsoop.timer_hours*3600)) / 60);
            catsoop.timer_seconds = catsoop.timer_remaining - (catsoop.timer_hours*3600) - (catsoop.timer_minutes*60);
            $('#timer').html('Time Remaining: ');
            $('#timer').append('' + catsoop.timer_hours + ' hours, ' + catsoop.timer_minutes + ' minutes, ' + catsoop.timer_seconds + ' seconds');
        }
    }
    catsoop.timer_counter = setInterval(catsoop.timer,1000);
    catsoop.timer();
});
