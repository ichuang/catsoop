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
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


catsoop.switch_buttons = function (qname, enabled){
    document.getElementById('cs_qdiv_'+qname).querySelectorAll('button').forEach(function(b){b.disabled=!enabled});
}


document.addEventListener("DOMContentLoaded", function(event) {
    document.querySelectorAll('button').forEach(function(b){b.disabled=false});
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
        var elts = document.querySelectorAll('input[name^=__'+names[i]+']');
        for (var i=0; i<elts.length; i++){
            names.push(elts[i].name)
        }
    }
    var out = {};

    var promises = [];
    for (var i=0; i<names.length; i++){
        var name = names[i];
        var field = document.querySelector('input[name="'+name+'"]');
        catsoop.switch_buttons(name, false);
        document.getElementById(name+'_loading').style.display = '';
        document.getElementById(name+'_score_display').style.display = 'none';
        promises.push(catsoop.load_one_form_element(field, name, out, action));
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
            document.getElementById(name+'_loading').style.display = 'none';
            document.getElementById(name+'_score_display').style.display = '';
            catsoop.switch_buttons(name, true);
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
                    document.getElementById(name+'_'+i).innerHTML = (thisone[i] || '');
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


catsoop.ajaxErrorCallback = function(name) {return function(req_status, msg){
    catsoop.switch_buttons(name, true);
    document.getElementById(name+'_loading').style.display = 'none';
    document.getElementById(name+'_message').innerHTML = ('<div class="impsolution"><font color="red"><b>ERROR</b></font>: Request Failed.  Please send the following information to a staff member:<br />'+'<textarea cols="60" rows="10">'+req_status+'\n'+msg+'\n'+'</textarea>'+'</div>');
}}


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

catsoop.confirmAndViewAnswer = function(name) {
    swal({
      title: 'Are you sure?',
      text: catsoop.viewans_confirm,
      type: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#3085d6',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Yes, view answer!'
    }).then(function(x) {
        if(x.value){
            catsoop.viewanswernow(name);
        }
    })
};
