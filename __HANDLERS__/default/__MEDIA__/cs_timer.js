/*  This file is part of CAT-SOOP
 *  Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
 *
 *  This program is free software: you can redistribute it and/or modify it
 *  under the terms of the GNU Affero General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or (at your
 *  option) any later version.
 *
 *  This program is distributed in the hope that it will be useful, but WITHOUT
 *  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 *  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public
 *  License for more details.
 *
 *  You should have received a copy of the GNU Affero General Public License
 *  along with this program.  If not, see
 *  <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.
 */

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
