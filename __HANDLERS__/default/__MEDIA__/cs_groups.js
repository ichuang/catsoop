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

function _encode_form(d){
    var encoded_form_pairs = [];
    for (var name in d){
        encoded_form_pairs.push(encodeURIComponent(name) + '=' + encodeURIComponent(d[name]));
    }
    return encoded_form_pairs.join('&').replace(/%20/g, '+');
}

function _sorted_keys(obj){
    var out = [];
    for (k in obj){
        if (obj.hasOwnProperty(k)){
            out.push(k);
        }
    }
    out.sort();
    return out;
}

catsoop.groups_buttons = ["cs_groups_addtogroup", "cs_groups_newpartners", "cs_groups_reassign"];
catsoop.groups_selectors = ["cs_groups_name1", "cs_groups_name2", "cs_groups_nameadd"];

catsoop.groups_clear_ui = function() {
    for (var i of catsoop.groups_buttons){
        document.getElementById(i).disabled = true;
    }
    for (var i of catsoop.groups_selectors){
        document.getElementById(i).innerHTML = '';
    }
}

catsoop.groups_enable_buttons = function() {
    for (var i of catsoop.groups_buttons){
        document.getElementById(i).disabled = false;
    }
}

catsoop.update_group_list = function () {
    catsoop.groups_clear_ui();
    var all_students;
    var partner_list;
    var section = document.getElementById('section').value;
    document.getElementById('cs_groups_section').innerText = '' + section;
    var table = document.getElementById('cs_groups_table');
    var request = new XMLHttpRequest();
    request.onload = function(){
        msg = JSON.parse(request.response);
        console.log(JSON.stringify(msg));
        if (!msg.ok){
            table.innerHTML = '<font color="red">OH NO!</font> ' + msg.error;
        }else{
            table.style.border = 'none';
            msg = msg.groups;
            var allgroups = _sorted_keys(msg);
            if (Object.keys(msg).length == 1){
                table.innerHTML = 'No groups currently assigned.';
            }else{
                table.innerHTML = '<ul></ul>';
                var ul = table.getElementsByTagName('ul')[0];
                for (var i=0; i<allgroups.length; i++){
                    var grp = allgroups[i];
                    if (grp === '_unpartnered') continue;
                    var members = msg[grp];
                    var li = document.createElement('li');
                    var b = document.createElement('b');
                    b.innerText = 'Group ' + grp + ': ';
                    li.appendChild(b);
                    for (var j=0; j<members.length; j++){
                        if (j>0) li.appendChild(document.createTextNode(', '));
                        li.appendChild(document.createTextNode(members[j] + ' ('));
                        var a = document.createElement('a');
                        a.style.cursor = 'pointer';
                        a.addEventListener('click', (function(name, group){return function(){catsoop.groups_remove(name, group)}})(members[j], grp));
                        a.classList = 'remove';
                        a.title = grp + ' ' + members[j];
                        a.innerText = 'remove'
                        li.appendChild(a);
                        li.appendChild(document.createTextNode(')'));
                    }
                    ul.append(li);
                }
            }
            var un = msg['_unpartnered'];
            for (var i of catsoop.groups_selectors){
                var menu = document.getElementById(i);
                un.sort();
                for (var j=0; j<un.length; j++){
                    var n = un[j];
                    var opt = document.createElement('option');
                    opt.value = n;
                    opt.innerText = n;
                    menu.appendChild(opt);
                }
            }
            var grpname = document.getElementById('cs_groups_groupadd');
            grpname.innerHTML = '';
            for (var i of catsoop.group_names){
                var opt = document.createElement('option');
                opt.value = i;
                opt.innerText = i;
                grpname.appendChild(opt);
            }
        }
        catsoop.groups_enable_buttons();
    }

    var form = _encode_form({'api_token': catsoop.api_token,
                             'path': JSON.stringify(catsoop.path_info),
                             'section': section});
    request.open('POST', catsoop.url_root + '/cs_util/api/groups/list_groups', true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
}

catsoop.groups_partner_all = function() {
    catsoop.groups_clear_ui();
    var section = document.getElementById("section").value;
    var form = _encode_form({'api_token': catsoop.api_token,
                             'path': JSON.stringify(catsoop.path_info),
                             'section': section});
    var request = new XMLHttpRequest();
    request.onload = catsoop.update_group_list;
    request.open('POST', catsoop.url_root + '/cs_util/api/groups/make_all_groups', true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
    catsoop.groups_enable_buttons();
}

catsoop.groups_confirm_and_partner_all = function() {
    catsoop.modal('Are you sure?', 'Really repartner all students?  This will delete all pre-existing groups and randomly assign everyone a new partner.', false)
    .then(function(x) {
            catsoop.groups_partner_all(name);
    })
    .catch(function(){});
}

catsoop.groups_add = function(){
    var name = document.getElementById("cs_groups_nameadd").value;
    var grp = document.getElementById("cs_groups_groupadd").value;
    catsoop.groups_clear_ui();
    var form = _encode_form({'api_token': catsoop.api_token,
                             'path': JSON.stringify(catsoop.path_info),
                             'username': name,
                             'group': grp});
    var request = new XMLHttpRequest();
    request.onload = catsoop.update_group_list;
    request.open('POST', catsoop.url_root + '/cs_util/api/groups/add_to_group', true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
    catsoop.groups_enable_buttons();
}

catsoop.groups_remove = function(name, grp){
    catsoop.groups_clear_ui();
    var form = _encode_form({'api_token': catsoop.api_token,
                             'path': JSON.stringify(catsoop.path_info),
                             'username': name,
                             'group': grp});
    var request = new XMLHttpRequest();
    request.onload = catsoop.update_group_list;
    request.open('POST', catsoop.url_root + '/cs_util/api/groups/remove_from_group', true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
    catsoop.groups_enable_buttons();
}

catsoop.groups_partner = function(){
    var name1 = document.getElementById("cs_groups_name1").value;
    var name2 = document.getElementById("cs_groups_name2").value;
    catsoop.groups_clear_ui();
    var form = _encode_form({'api_token': catsoop.api_token,
                             'path': JSON.stringify(catsoop.path_info),
                             'username1': name1,
                             'username2': name2});
    var request = new XMLHttpRequest();
    request.onload = catsoop.update_group_list;
    request.open('POST', catsoop.url_root + '/cs_util/api/groups/partner', true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    request.send(form);
    catsoop.groups_enable_buttons();
}

document.addEventListener('DOMContentLoaded', function(){
    catsoop.update_group_list();
    document.getElementById('section').addEventListener('change', catsoop.update_group_list);
    document.getElementById('cs_groups_reassign').addEventListener('click', catsoop.groups_confirm_and_partner_all);
    document.getElementById('cs_groups_addtogroup').addEventListener('click', catsoop.groups_add);
    document.getElementById('cs_groups_newpartners').addEventListener('click', catsoop.groups_partner);
});
