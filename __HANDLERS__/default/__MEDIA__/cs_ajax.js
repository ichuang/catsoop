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

$(':button').prop("disabled",false);

function switch_buttons(name, enabled){
    $(":button", $("#cs_qdiv_"+name)).prop("disabled", !enabled);
}

function doFiles(lastDeferred, into, files){
    var name = null;
    var file = null;
    var num = files.length;
    var f = null;
    var funcs = [];
    for (var i=0; i<num; i++){
        name = files[i][0];
        file = files[i][1];
        if (i==0){
            f = function(NAME, thisIx){return function(){
                var d = new $.Deferred();
                d.done(function(){lastDeferred.resolve();});
                var fr = new FileReader();
                fr.onload = function(THING){return function(e){
                                         into[NAME]=[(files[thisIx][1]).name, e.target.result];
                                         THING.resolve();
                                       };}(d);
                fr.readAsDataURL(files[thisIx][1]);
            }}(name, i);
            funcs.push(f);
        }else{
            f = function(whichIx,NAME, thisIx){return function(){
                var d = new $.Deferred();
                d.done(function(){funcs[whichIx]();});
                var fr = new FileReader();
                fr.onload = function(THING){return function(e){
                                         into[NAME]=[(files[thisIx][1]).name, e.target.result];
                                         THING.resolve();
                                       };}(d);
                fr.readAsDataURL(files[thisIx][1]);
            };}(funcs.length-1,name,i);
            funcs.push(f);
        }
    }

    if(files.length==0){
        lastDeferred.resolve();
    }else{
        funcs[funcs.length-1]();
    }
}

function cs_ajaxrequest(names, action){
    var fileD = new $.Deferred();
    var FILES = [];
    var num = names.length;
    var names_to_add = [];
    for (var i=0; i < num; i++){
        $(':input[name^=__'+names[i]+']').each(function(x,y){names_to_add.push(y.name)});
    }
    for (var i=0; i < names_to_add.length; i++){
        names.push(names_to_add[i]);
    }
    var out = {};
    num = names.length;
    for (var i=0; i<num; i++){
        var name = names[i];
        var field = $(':input[name="'+name+'"]');
        switch_buttons(name, false);
        $('#'+name+'_loading').show();
        $('#'+name+'_score_display').hide();
        if (field.attr('type')==="file"){
            if (field[0].files.length>0){
                var file = field[0].files[0];
                FILES.push([name, file]);
            }else{
                if(action==="submit"){
                    alert("Please select a file to upload.");
                    switch_buttons(name,true);
                    $('#'+name+'_loading').hide();
                    $('#'+name+'_score_display').show();
                    return;
                }else{
                    out[name] = "";
                }
            }
        }else{
            out[name] = field.val();
        }
    }
    fileD.done(function(){sendRequest(names, action, out);});
    doFiles(fileD, out, FILES);
}

var cs_ajaxDoneCallback = function(data, path, count) { return function(msg, textStatus, jqXHR){
                    try{
                        if(Object.keys(msg).length > 0){
                            for (var name in msg){
                                var thisone = msg[name];
                                $('#'+name+'_loading').hide();
                                $('#'+name+'_score_display').show();
                                if('rerender' in thisone){
                                    $('#'+name+'_rendered_question').html(thisone['rerender']);
                                }
                                if('clear' in thisone){
                                    $('#'+name+'_solution_container').removeClass();
                                    $('#'+name+'_solution').html('');
                                    $('#'+name+'_solution_explanation').html('');
                                }
                                if ('save' in thisone){
                                    $('#'+name+'_response').html('');
                                }
                                if('answer' in thisone){
                                    $('#'+name+'_solution_container').removeClass();
                                    $('#'+name+'_solution_container').addClass('solution');
                                    $('#'+name+'_solution').html(thisone['answer']);
                                    cs_render_all_math($('#cs_qdiv_'+name)[0]);
                                }
                                if('explanation' in thisone){
                                    $('#'+name+'_solution_explanation').html(thisone['explanation']);
                                    cs_render_all_math($('#cs_qdiv_'+name)[0]);
                                }
                                if (thisone['error_msg'] !== undefined){
                                    $('#'+name+'_response').html('<div class="impsolution"><font color="red"><b>ERROR</b></font>:<br />'+thisone['error_msg']+'</div>');
                                }
                                $('#'+name+'_score_display').html(thisone['score_display']);
                                $('#'+name+'_response').html(thisone['response']);
                                $('#'+name+'_nsubmits_left').html(thisone['nsubmits_left']);
                                $('#'+name+'_buttons').html(thisone['buttons']);
                                if(thisone['val'] !== undefined){
                                    $('#'+name).val(thisone['val']);
                                }
                                switch_buttons(name, true);
                            }
                        }else{
                            switch_buttons(name, true);
                            $('#'+name+'_loading').hide();
                            alert('Error: no response');
                        }
                }catch(err){
                   if(count < 5){
                       console.log('retrying request: attempt ' + (count+2));
                       setTimeout(function(){$.ajax({type:'POST',
                               url: path,
                               async: 'false',
                               data: data}).done(cs_ajaxDoneCallback(data, path, count+1));}, 250);
                   }else{
                       var dnames = JSON.parse(data['names']);
                       console.log('giving up on retrying request');
                       for(var ix in dnames){
                           var name = dnames[ix];
                           $('#'+name+'_response').html('<div class="impsolution"><font color="red"><b>ERROR</b></font>: Request Failed.  Please try again, and send the following information to a staff member:<br />'+'<textarea cols="60" rows="10">'+JSON.stringify(jqXHR)+'\n'+JSON.stringify(err)+'</textarea>'+'</div>');
                           switch_buttons(name, true);
                            $('#'+name+'_loading').hide();
                       }
                   }
               }
}}

function sendRequest(names,action,send){
    var form = {};
    for (var key in send){if (send.hasOwnProperty(key)){form[key] = send[key];}}
    var d = {action: action,
             names: JSON.stringify(names),
             api_token: cs_api_token,
             data: JSON.stringify(form)};
    if (cs_imp != '') d['as'] = cs_imp;
    $.ajax({type:'POST',
            url: cs_this_path,
            async: 'false',
            data: d}).done(cs_ajaxDoneCallback(d, cs_this_path, 0));
};
function cs_submit(name){cs_ajaxrequest([name],'submit');};
function cs_check(name){cs_ajaxrequest([name],'check');};
function cs_viewanswernow(name){cs_ajaxrequest([name],'viewanswer');};
function cs_clearanswer(name){cs_ajaxrequest([name],'clearanswer');};
function cs_viewexplanation(name){cs_ajaxrequest([name],'viewexplanation');};
function cs_grade(name){cs_ajaxrequest([name, name+'_grading_score', name+'_grading_comments'],'grade');};
function cs_lock(name){cs_ajaxrequest([name],'lock');};
function cs_unlock(name){cs_ajaxrequest([name],'unlock');};
function cs_save(name){cs_ajaxrequest([name],'save');};
function cs_copy(name){cs_ajaxrequest([name],'copy');};
function cs_copy_seed(name){cs_ajaxrequest([name],'copy_seed');};
function cs_new_seed(name){cs_ajaxrequest([name],'new_seed');};
function cs_viewanswer(name){cs_viewanswer_skipalert(name) && cs_viewanswernow(name);};
function cs_viewanswer_skipalert(name){
    var i = cs_skip_alert.length;
    while (i--){
        if (cs_skip_alert[i] === name){
            return true
        }
    }
    return confirm(cs_viewans_confirm);
}
