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
    catsoop.queue.myclaimed = null;
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
        if (m.type === 'hello' && !m.ok){
            // if we get this message, we weren't able to log in successfully,
            // so we'll just close the connection.
            catsoop.queue.ws.close();
        }else if(m.type == 'ping'){
            catsoop.queue.ws.send(JSON.stringify({type: 'pong'}));
        }else if (m.type == 'queue'){
            // this should happen near to when we first connect.  we receive
            // the current state of the queue.
            // sort by started time and replace the actual queue.
            m.queue.sort(function(a, b){
                return a.started_time - b.started_time;
            });
            catsoop.queue.queue = m.queue;
            if (typeof catsoop.queue.render_queue !== 'undefined'){
                catsoop.queue.render_queue();
            }
        }else if (m.type == 'update'){
            if (catsoop.queue.queue === null){
                return;
            }
            // we'll receive one of these every time something changes in the
            // DB.  it's up to us to figure out what that means for what we're
            // tracking.
            var news = m.entries;
            // combine new and old queues
            var newqueue = catsoop.queue.queue.concat(news);
            // sort entries entries by updated_time
            newqueue.sort(function(a, b){
                return a.updated_time - b.updated_time;
            });
            // keep only the _most recently updated_ entry for each id
            var seen = new Set();
            var toremove = [];
            for (var i = newqueue.length-1; i >= 0; i--){
                var entry = newqueue[i];
                if (seen.has(entry.id)){
                    toremove.push(i);
                }
                seen.add(entry.id);
            }
            for (var i of toremove){
                newqueue.splice(i, 1);
            }
            // now, filter the queue entries to keep only the active ones.
            newqueue = newqueue.filter(function(elt){
                return elt.active;
            });
            // now sort by started time
            newqueue.sort(function(a, b){
                return a.started_time - b.started_time;
            });
            // and find my entry and/or my claim.
            var myentry = null;
            var myclaimed = null;
            var curpos = 1;
            for(var i = 0; i < newqueue.length; i++){
                var entry = newqueue[i];
                if (entry.claimant === catsoop.username){
                    myentry = [curpos, entry];
                }else if (entry.name === catsoop.username){
                    myclaimed = [curpos, entry];
                }
                if (entry.claimant === null){
                    // not been claimed; this counts against the position.
                    curpos++;
                }
            }
            catsoop.queue.myentry = myentry;
            catsoop.queue.myclaimed = myclaimed;
            // and, of course, replace catsoop.queue.queue
            catsoop.queue.queue = newqueue;
            // that will handle the updates.  now, rerender the queue.  the trick
            // here is that we won't ever define this, because the way the queue
            // wants to show up is going to be different for everyone (and even for
            // different pages within the same course).
            if (typeof catsoop.queue.render_queue !== 'undefined'){
                catsoop.queue.render_queue();
            }
        }
    }

    catsoop.queue.ws.onclose = function(){
        catsoop.queue.queue = null;
        catsoop.queue.myentry = null;
        catsoop.queue.myclaimed = null;
        delete catsoop.queue.ws;
        if (typeof catsoop.queue.render_queue !== 'undefined'){
            catsoop.queue.render_queue();
        }
    }
});
