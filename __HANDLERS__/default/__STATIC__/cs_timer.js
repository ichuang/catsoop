/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Affero General Public License as published by the
 * Free Software Foundation, either version 3 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License
 * for more details.
 *
 * As an additional permission under GNU AGPL version 3 section 7, you may
 * distribute non-source (e.g., minimized or compacted) forms of the code in
 * this file without the copy of the GNU AGPL normally required by section 4,
 * provided you include this license notice and a URL through which recipients
 * can access the Corresponding Source.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

var timerelt = document.createElement('div');
timerelt.setAttribute('id', 'timer');
timerelt.classList.add('response');
timerelt.style = 'position:fixed;right:10px;bottom:0px;width:auto;z-index:10000;';
document.body.append(timerelt);

document.addEventListener("DOMContentLoaded", function(event) {
    var timerelt = document.getElementById('timer');
    catsoop.timer_remaining = catsoop.timer_due-catsoop.timer_now;
    catsoop.timer = function () {
        catsoop.timer_remaining=catsoop.timer_remaining-1;
        if(catsoop.timer_remaining <= 0){
            clearInterval(catsoop.timer_counter);
            catsoop.ajaxrequest(catsoop.all_questions,'lock');
        }else{
            if (catsoop.timer_remaining%20 == 0){
                setTimeout(function(){
                    var request = new XMLHttpRequest();
                    request.onload = function(){
                        catsoop.timer_remaining = catsoop.timer_due - parseInt(request.response);
                    }
                    request.open('GET', catsoop.time_url, true);
                    request.send();
                }, Math.floor((Math.random() * 2000) + 1000));
            }
            catsoop.timer_hours = Math.floor(catsoop.timer_remaining / 3600);
            catsoop.timer_minutes = Math.floor((catsoop.timer_remaining - (catsoop.timer_hours*3600)) / 60);
            catsoop.timer_seconds = catsoop.timer_remaining - (catsoop.timer_hours*3600) - (catsoop.timer_minutes*60);
            timerelt.innerText = ('Time Remaining: ' + catsoop.timer_hours + ' hours, ' + catsoop.timer_minutes + ' minutes, ' + catsoop.timer_seconds + ' seconds');
        }
    }
    catsoop.timer_counter = setInterval(catsoop.timer,1000);
    catsoop.timer();
});
