/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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


catsoop.switch_buttons = function (qname, enabled){
    for(var b of Array.prototype.slice.call(document.getElementById(qname + '_buttons').getElementsByTagName('button'))) b.disabled = !enabled;
}


document.addEventListener("DOMContentLoaded", function(event) {
    for(var b of Array.prototype.slice.call(document.getElementsByTagName('button'))) b.disabled = false;
});


catsoop.setTimeSince = function (name, start, sync){
    var now = (new Date()).valueOf()/1000 - sync; // our estimate of the server's current time
    var diff = now - start;
    var time = {};
    time.days = (diff / 86400) | 0;
    diff -= (time.days * 86400);
    time.hours = (diff / 3600) | 0;
    diff -= (time.hours * 3600);
    time.minutes = (diff / 60) | 0;
    diff -= (time.minutes * 60);
    time.seconds = diff | 0;
    var msg = '';
    for (var i of ['days', 'hours', 'minutes', 'seconds']){
        if (time[i] > 0){
            if (msg !== ''){
                msg += ', ';
            }
            msg = msg + ((time[i]).toString() + ' ' + i);
            if (time[i] == 1){
                msg = msg.slice(0, -1);
            }
        }
    }
    document.getElementById(name + '_ws_running_time').innerText = ' (running for around ' + msg + ')';
}


catsoop.load_one_form_element = function(elt, name, into, action){
    return new Promise(function(resolve, reject){
        if (elt.getAttribute('type') === 'file'){
            if(elt.files.length > 0){
                var file = elt.files[0];
                var fr = new FileReader();
                fr.onload = function(e){
                    into[name] = [file.name, e.target.result];
                    resolve();
                }
                fr.readAsDataURL(file);
            }else if(action === "submit"){
                alert("Please select a file to upload");
                reject();
            }else{
                into[name] = "";
                resolve();
            }
        }else{
            into[name] = elt.value;
            resolve();
        }
    });
}


catsoop.ajaxrequest = function (names, action, done_function){
    for (var i=0; i < names.length; i++){
        var elts = document.querySelectorAll('[name^=__'+names[i]+']');
        for (var j=0; j<elts.length; j++){
            names.push(elts[j].name)
        }
    }
    var out = {};

    var promises = [];
    for (var i=0; i<names.length; i++){
        var name = names[i];
        var field = document.querySelector('[name="'+name+'"]');
        if (document.getElementById(name+'_buttons') !== null){
            catsoop.switch_buttons(name, false);
            document.getElementById(name+'_loading').style.display = '';
            document.getElementById(name+'_score_display').style.display = 'none';
        }
        if(document.getElementById(name) !== null){
            promises.push(catsoop.load_one_form_element(field, name, out, action));
        }
    }
    Promise.all(promises).then(
    function(){
        //success.  all fields loaded, submit the request
        catsoop.send_request(names, action, out, done_function);
    },

    function(){
        //failure.  reset loading and score displays.
        for (var i=0; i<names.length; i++){
            var name = names[i];
            if (!name.startsWith('__')){
                document.getElementById(name+'_loading').style.display = 'none';
                document.getElementById(name+'_score_display').style.display = '';
                catsoop.switch_buttons(name, true);
            }
        }
    });
}

catsoop.run_all_scripts = function(selector){
    var newscripts = document.querySelectorAll('#'+selector+' script');
    for(var i=0; i<newscripts.length;i++){
        eval(newscripts[i].innerText);
    }
}

catsoop.ajaxDoneCallback = function(data, path, count) { return function(req_status, msg){
    try{
        if(req_status < 200 || req_status >= 400){
            throw new Error('error code from server: ' + req_status)
        }
        msg = JSON.parse(msg);
        if(Object.keys(msg).length > 0){
            for (var name in msg){
                var thisone = msg[name];
                document.getElementById(name+'_loading').style.display = 'none';
                document.getElementById(name+'_score_display').style.display = '';
                if('rerender' in thisone){
                    document.getElementById(name+'_rendered_question').innerHTML = thisone['rerender'];
                    catsoop.run_all_scripts(name+'_rendered_question');
                }
                if('clear' in thisone){
                    document.getElementById(name+'_solution_container').classList = [];
                    document.getElementById(name+'_solution').innerHTML = '';
                    document.getElementById(name+'_solution_explanation').innerHTML = '';
                }
                if ('save' in thisone){
                    document.getElementById(name+'_message').innerHTML = '';
                }
                if('answer' in thisone){
                    document.getElementById(name+'_solution_container').classList = ['solution'];
                    document.getElementById(name+'_solution').innerHTML = thisone['answer'];
                    catsoop.run_all_scripts(name+'_solution');
                }
                if('explanation' in thisone){
                    document.getElementById(name+'_solution_explanation').innerHTML = thisone['explanation'];
                    catsoop.run_all_scripts(name+'_solution_explanation');
                }
                if (thisone['error_msg'] !== undefined){
                    document.getElementById(name+'_message').innerHTML = '<div class="impsolution"><font color="red"><b>ERROR</b></font>:<br />'+thisone['error_msg']+'</div>';
                }
                for (var i of ['score_display', 'message', 'nsubmits_left', 'buttons']){
                    if(typeof thisone[i] !== 'undefined'){
                        document.getElementById(name+'_'+i).innerHTML = thisone[i];
                    }
                }
                catsoop.run_all_scripts(name+'_message');
                if(thisone['val'] !== undefined){
                    document.getElementById(name).value = thisone['val'];
                }
                catsoop.render_all_math(document.getElementById('cs_qdiv_'+name));
                catsoop.switch_buttons(name, true);
            }
        }else{
            catsoop.switch_buttons(name, true);
            document.getElementById(name+'_loading').style.display = 'none';
            alert('Error: no message');
        }
    }catch(err){
        var dnames = JSON.parse(data['names']);
        for(var ix in dnames){
            var name = dnames[ix];
            document.getElementById(name+'_message').innerHTML = '<div class="impsolution"><font color="red"><b>ERROR</b></font>: Request Failed.  Please try again after a while. <pre>' + err.stack + '</pre></div>';
            catsoop.switch_buttons(name, true);
            document.getElementById(name+'_loading').style.display = 'none';
        }
    }
}}


catsoop.ajaxErrorCallback = function(name) {
    return function(req_status, msg){
        catsoop.switch_buttons(name, true);
        document.getElementById(name+'_loading').style.display = 'none';
        document.getElementById(name+'_message').innerHTML = ('<div class="impsolution"><font color="red"><b>ERROR</b></font>: Request Failed.<br />'+'<pre>'+req_status+'\n'+msg+'\n'+'</pre>'+'</div>');
    }
}


catsoop.send_request = function(names,action,send,done_function){
    var form = {};
    for (var key in send){if (send.hasOwnProperty(key)){form[key] = send[key];}}
    var d = {action: action,
             names: JSON.stringify(names),
             api_token: catsoop.api_token,
             data: JSON.stringify(form)};
    if (catsoop.imp != '') d['as'] = catsoop.imp;

    var encoded_form_pairs = [];
    for (var name in d){
        encoded_form_pairs.push(encodeURIComponent(name) + '=' + encodeURIComponent(d[name]));
    }
    var form = encoded_form_pairs.join('&').replace(/%20/g, '+');

    var request = new XMLHttpRequest();
    request.onload = function(){
        catsoop.ajaxDoneCallback(d, catsoop.this_path, 0)(request.status, request.response);
        if(typeof done_function !== "undefined"){
            done_function(true);
        }
    }
    request.onerror = function(){
        catsoop.ajaxErrorCallback(names[0])(request.status, request.response);
        if(typeof done_function !== "undefined"){
            done_function(false);
        }
    }
    request.open('POST', catsoop.this_path, true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
};


catsoop.submit = function (name){catsoop.ajaxrequest([name],'submit');};
catsoop.check = function (name){catsoop.ajaxrequest([name],'check');};
catsoop.viewanswernow = function (name){catsoop.ajaxrequest([name],'viewanswer');};
catsoop.clearanswer = function (name){catsoop.ajaxrequest([name],'clearanswer');};
catsoop.viewexplanation = function (name){catsoop.ajaxrequest([name],'viewexplanation');};
catsoop.grade = function (name){catsoop.ajaxrequest([name, name+'_grading_score', name+'_grading_comments'],'grade');};
catsoop.lock = function (name){catsoop.ajaxrequest([name],'lock');};
catsoop.unlock = function (name){catsoop.ajaxrequest([name],'unlock');};
catsoop.save = function (name){catsoop.ajaxrequest([name],'save');};
catsoop.copy = function (name){catsoop.ajaxrequest([name],'copy');};
catsoop.copy_seed = function (name){catsoop.ajaxrequest([name],'copy_seed');};
catsoop.new_seed = function (name){catsoop.ajaxrequest([name],'new_seed');};
catsoop.viewanswer = function (name){
    if (catsoop.viewanswer_skipalert(name)) catsoop.viewanswernow(name);
    else catsoop.confirmAndViewAnswer(name);
};
catsoop.viewanswer_skipalert = function (name){
    return catsoop.skip_alert.indexOf(name) !== -1;
};


catsoop.modal = function(header, text, input, cancel){
    input = typeof input === 'undefined' ? false : input;
    cancel = typeof cancel === 'undefined' ? true : cancel;
    return new Promise(function(resolve, reject){
        var background = document.createElement('div');
        background.addEventListener('click', function(){
            document.body.removeChild(background);
            reject(false);
        });
        background.classList = ['modal-background'];

        var content = document.createElement('div');
        content.classList = ['modal-content'];
        content.addEventListener('click', function(e){
            e.stopPropagation();
        });

	if ('parentIFrame' in window) {
	    var irr = function(x){	// receive parent page position info, including scrollTop
		console.log(x);
		var top = x.scrollTop - x.clientHeight + 400;
		content.style.marginTop = String(top) + "px";
		content.style.marginLeft = "auto";
		content.style.marginRight = "auto";
		content.style.marginBottom = "auto";
	    }
	    window.parentIFrame.getPageInfo(irr);
	}

        var mbody = document.createElement('div');
        mbody.classList = ['modal-body'];

        var close_button = document.createElement('div');
        close_button.classList = ['modal-close'];
        close_button.innerHTML = '&times;'
        close_button.addEventListener('click', function(){
            document.body.removeChild(background);
            reject(false);
        });
        mbody.append(close_button);

        var title = document.createElement('h3');
        title.appendChild(document.createTextNode(header));
        mbody.appendChild(title);

        var body = document.createElement('p');
        body.innerHTML = text + '<br/>';
        mbody.appendChild(body);

        var buttons = document.createElement('span');
        var okay_button = document.createElement('button');
        okay_button.innerText = input ? 'Submit' : 'OK';
        okay_button.classList = ['btn'];
        okay_button.addEventListener('click', function(){
            document.body.removeChild(background);
            resolve(input ? input_field.value : true);
        });
        if (input){
            var input_field = document.createElement('input');
            input_field.classList = ['modal-input'];
            input_field.setAttribute('type', 'text');
            body.appendChild(input_field);
            input_field.addEventListener('keypress', function(e){
                if (e.which == 13){
                    okay_button.click();
                }
            });
        }

        if (cancel){
            var cancel_button = document.createElement('button');
            cancel_button.innerText = 'Cancel';
            cancel_button.classList = ['btn'];
            cancel_button.addEventListener('click', function(){
                document.body.removeChild(background);
                reject(false);
            });
        }
        buttons.appendChild(okay_button);
        if (cancel) {
            buttons.appendChild(document.createTextNode(' '));
            buttons.appendChild(cancel_button);
        }
        buttons.appendChild(cancel_button);
        mbody.appendChild(buttons);

        content.appendChild(mbody);
        background.appendChild(content);
        document.body.appendChild(background);
    });
}

catsoop.confirmAndViewAnswer = function(name) {
    catsoop.modal('Are you sure?', catsoop.viewans_confirm, false).then(function(x) {
        catsoop.viewanswernow(name);
    }).catch(function(){});
};
