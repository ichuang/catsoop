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
    if (!catsoop.queue_enabled ||
           typeof catsoop.queue_location === 'undefined' ||
           catsoop.queue_location === null ||
           catsoop.api_token === null){
        return;
    }
    catsoop.queue = {};
    catsoop.queue.queue = null;
    catsoop.queue.myentry = null;
    catsoop.queue.known_keys = new Set();
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
        var m = JSON.parse(event.data);
        console.log(m);
        if (m.type === 'hello' && !m.ok){
            // if we get this message, we weren't able to log in successfully,
            // so we'll just close the connection.
            catsoop.queue.ws.close();
        }else if(m.type == 'ping'){
            catsoop.queue.ws.send(JSON.stringify({type: 'pong'}));
        }else if (m.type == 'queue'){
            // this should happen near to when we first connect.  we receive
            // the current state of the queue.
            catsoop.queue.queue = m.queue;
            catsoop.queue.known_keys = new Set();
            var m_t = null;
            for (var i = 0; i < m.queue.length; i ++){
                catsoop.queue.known_keys.add(m.queue[i].username);
                if (m_t === null || m.queue[i].updated_time > m_t){
                    m_t = m.queue[i].updated_time;
                }
            }
            if (m_t !== null){
                catsoop.queue.ws.send(JSON.stringify({type: 'max_time', time: m_t}));
            }
        }else if (m.type == 'update'){
            if (catsoop.queue.queue === null){
                return;
            }
            console.log(catsoop.queue)
            // we'll receive one of these every time something changes in the
            // DB.  it's up to us to figure out what that means for what we're
            // tracking.
            var news = m.entries;
            var curix = 0;
            // we'll loop over all the new entries (probably just one, given
            // the default queue timing)
            var m_t = null;
            for (var i = 0; i < news.length; i++){
                var entry = news[i];
                if (m_t === null || entry.updated_time > m_t){
                    m_t = entry.updated_time;
                }
                if (entry.active){
                    if (catsoop.queue.known_keys.has(entry.username)){
                        // we already know this key.  just replace its entry
                        for (var j = 0; j < catsoop.queue.queue.length; j++){
                            var oentry = catsoop.queue.queue[j];
                            if (oentry.username === entry.username){
                                catsoop.queue.queue[j] = entry;
                                break;
                            }
                        }
                    }else{
                        // this is a new key.  find the right spot in the array
                        // and add it in.
                        var j = 0;
                        var broke = false;
                        for (j = 0; j < catsoop.queue.queue.length; j++){
                            var oentry = catsoop.queue.queue[j];
                            if (oentry.started_time > entry.started_time){
                                catsoop.queue.queue.splice(j, 0, entry);
                                broke = true;
                                break;
                            }
                        }
                        if (!broke){
                            catsoop.queue.queue.splice(j, 0, entry);
                        }
                    }
                    // regardless of whether we added or replaced, we want to
                    // update "myentry" and the currently know keys.
                    if (entry.username === catsoop.username){
                        catsoop.queue.myentry = entry;
                    }
                    catsoop.queue.known_keys.add(entry.username);
                    console.log(catsoop.queue)
                }else{
                    // this thing is no longer active.  let's kill it.
                    for (var j = 0; j < catsoop.queue.queue.length; j++){
                        var oentry = catsoop.queue.queue[j];
                        if (oentry.username === entry.username){
                            catsoop.queue.queue.splice(j, 1);
                            break;
                        }
                    }
                    catsoop.queue.known_keys.delete(entry.username);
                }
            }
            if (m_t !== null){
                catsoop.queue.ws.send(JSON.stringify({type: 'max_time', time: m_t}));
            }
        }
        // that will handle the updates.  now, rerender the queue.  the trick
        // here is that we won't ever define this, because the way the queue
        // wants to show up is going to be different for everyone (and even for
        // different pages within the same course).
        if (typeof catsoop.queue.render_queue !== 'undefined'){
            catsoop.queue.render_queue();
        }
    }

    catsoop.queue.ws.onclose = function(){
        catsoop.queue.queue = null;
        catsoop.queue.myentry = null;
        catsoop.queue.known_keys = new Set();
        delete catsoop.queue.ws;
        if (typeof catsoop.queue.render_queue !== 'undefined'){
            catsoop.queue.render_queue();
        }
    }
});
