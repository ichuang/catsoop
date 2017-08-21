/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
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
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

$(document).ready(function(){
    if (catsoop.queue_location === null) return;
    catsoop.queue = {}
    catsoop.queue.ws = new WebSocket(catsoop.queue_location);
    
    catsoop.queue.ws.onopen = function(){
        catsoop.queue.ws.send(JSON.stringify({
            type: 'hello',
            api_token: catsoop.api_token,
            course: catsoop.course,
            room: catsoop.queue_room,
        }));
    }
    
    catsoop.queue.ws.onmessage = function(event){
        console.log(event);
    }
});
