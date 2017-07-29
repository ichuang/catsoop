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
 *
 * Built on a skeleton from:
 * https://medium.com/@martin.sikora/node-js-websocket-simple-chat-tutorial-2def3a841b61
 */

"use strict";

var wsPort = parseInt(process.argv[2]);
process.title = 'catsoop_checker_reporter';

// keep going in the face of adversity
process.on('uncaughtException', function (err) {
    console.log('Caught exception: ' + err);
});

var webSocketServer = require('websocket').server;
var http = require('http');
var r = require('rethinkdb');
var rconn = null;

var allConnections = {};
var positions = {}; // mapping from magic number to [position, time, state]

r.connect({db: 'catsoop'}, function (err, conn){
    if (err) throw err;
    rconn = conn;
    // initialize our queue
    r.table('checker').changes({squash: false, includeInitial: true}).run(rconn, function(err, cursor){
        cursor.each(function(e, r){
            if (r.old_val != null && (r.new_val == null || r.new_val.progress == 2 || r.new_val.progress == 3)){
                // element deleted, or element switched to "complete"
                var t = r.old_val.time;
                // remove it
                delete positions[r.old_val.id];
                // slide everyone else down
                for(var i in positions){
                    if (positions[i][2] == 0 && positions[i][1] > t){
                        positions[i][0]--;
                        var c = allConnections[i];
                        if (c){
                            c.sendUTF(JSON.stringify({type: 'inqueue', position: positions[i][0]}));
                        }
                    }
                }
                if (r.new_val !== null){
                    var c = allConnections[r.new_val.id];
                    if (c){
                        var msg = r.new_val.response;
                        if(r.new_val.progress == 3){
                            msg = '<font color="red">' + msg + '</font>';
                        }
                        c.sendUTF(JSON.stringify({type: 'newresult', score_box: r.new_val.score_box, response: msg}));
                    }
                }
            }else if (r.old_val == null){
                // new entry
                if (r.new_val.progress != 0){
                    return;
                }
                // find its position
                var pos = 1;
                for(var i in positions){
                    if (positions[i][1] < r.new_val.time){
                        pos++;
                    }else{
                        positions[i][0]++;
                        var c = allConnections[i];
                        if (c){
                            c.sendUTF(JSON.stringify({type: 'inqueue', position: positions[i][0]}));
                        }
                    }
                }
                // and add it
                positions[r.new_val.id] = [pos, r.new_val.time, r.new_val.progress];
                var c = allConnections[r.new_val.id];
                if (c){
                    c.sendUTF(JSON.stringify({type: 'inqueue', position: pos}));
                }
            }else if (r.new_val.progress == 1){
                // we just started processing this entry
                positions[r.new_val.id] = [null, r.new_val.time, 1];
                var c = allConnections[r.new_val.id];
                if (c){
                    c.sendUTF(JSON.stringify({type: 'running',
                                              started: r.new_val.time_started.valueOf(),
                                              now: (new Date()).valueOf()}));
                }
            }else{
            }
        });
    });
});


var server = http.createServer(function(request, response) {});
server.listen(wsPort, function() {
    console.log((new Date()) + " Server is listening on port " + wsPort);
});

var wsServer = new webSocketServer({httpServer: server});

// when we receive a connection request, just add that connection to the
// mapping.
wsServer.on('request', function(request) {

    var connection = request.accept(null, request.origin);

    connection.on('message', function(message) {
        if (message.type === 'utf8') { // accept only text
            connection.sendUTF('{"type":"hello"}');
            try{
                var data = JSON.parse(message.utf8Data);
            }catch(e){
                connection.sendUTF(JSON.stringify({type: 'error', result: 'invalid request'}));
                return;
            }
            if (data.type == 'hello'){
                connection.catsoop_magic = data.magic;
                allConnections[data.magic] = connection;
                // check for current status in db
                r.table('checker').filter(r.row('id').eq(data.magic)).run(rconn, function(err, curs){
                    if (err) throw err;
                    curs.toArray(function (err, res){
                        if (err) throw err;
                        if (res.length > 0){
                            var o = res[res.length-1]; // most recent?
                            if (o.progress == 0){
                                // in queue.
                                if(data.magic in positions){
                                    connection.sendUTF(JSON.stringify({type: 'inqueue',
                                                                       position: positions[data.magic][0]}));
                                }
                            }else if (o.progress == 1){
                                connection.sendUTF(JSON.stringify({type: 'running',
                                                                   started: o.time_started.valueOf(),
                                                                   now: (new Date()).valueOf()}));
                            }else if (o.progress == 2){
                                // already done.
                                connection.sendUTF(JSON.stringify({type: 'newresult', score_box: o.score_box, response: o.response}));
                            }else if (o.progress == 3){
                                // error!
                                connection.sendUTF(JSON.stringify({type: 'newresult', score_box: o.score_box, response: '<font color="red">' + o.response + '</font>'}));
                            }
                        }
                    });
                });
            }
        }
    });

    connection.on('close', function(connection) {
            delete allConnections[connection.catsoop_magic];
    });

});
