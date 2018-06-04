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
 * distribute non-source (e.g., minimized or compacted) forms of that code
 * without the copy of the GNU AGPL normally required by section 4, provided
 * you include this license notice and a URL through which recipients can
 * access the Corresponding Source.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


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
        $('#'+i).prop('disabled', true);
    }
    for (var i of catsoop.groups_selectors){
        $("#"+i).html('');
    }
}

catsoop.groups_enable_buttons = function() {
    for (var i of catsoop.groups_buttons){
        $('#'+i).prop('disabled', false);
    }
}

catsoop.update_group_list = function () {
    catsoop.groups_clear_ui();
    var all_students;
    var partner_list;
    var section = $('#section').val();
    $('#cs_groups_section').text(section);
    var table = $('#cs_groups_table');
    $.ajax(catsoop.url_root + '/cs_util/api/groups/list_groups',
           {method: 'POST',
            data: {'api_token': catsoop.api_token,
                   'path': JSON.stringify(catsoop.path_info),
                   'section': section}}
    ).done(function(msg){
        console.log(JSON.stringify(msg));
        if (!msg.ok){
            table.html('<font color="red">OH NO!</font> ' + msg.error);
        }else{
            table.css('border', 'none');
            msg = msg.groups;
            var allgroups = _sorted_keys(msg);
            if (Object.keys(msg).length == 1){
                table.html('No groups currently assigned.')
            }else{
                table.html('<ul></ul>');
                var ul = table.children(':last-child');
                for (var i=0; i<allgroups.length; i++){
                    var grp = allgroups[i];
                    if (grp === '_unpartnered') continue;
                    var members = msg[grp];
                    ul.append('<li><b>Group ' + grp + '</b>: </li>');
                    var li = ul.children(':last-child');
                    for (var j=0; j<members.length; j++){
                        if (j>0) li.append(', ');
                        li.append(members[j] + ' (<a onclick="catsoop.groups_remove(\'' + members[j] + '\', \'' + grp + '\');" class="remove" title="' + grp + ' ' + members[j] + '">remove</a>)');
                    }
                }
            }
            var un = msg['_unpartnered'];
            for (var i of catsoop.groups_selectors){
                var menu = $("#"+i);
                un.sort();
                for (var j=0; j<un.length; j++){
                    var n = un[j];
                    menu.append('<option value="'+n+'">'+n+'</option>');
                }
            }
            var grpname = $('#cs_groups_groupadd');
            grpname.html = '';
            for (var i of catsoop.group_names){
                grpname.append('<option value="'+i+'">'+i+'</option>');
            }
        }
        catsoop.groups_enable_buttons();
    });
}

catsoop.groups_partner_all = function() {
    catsoop.groups_clear_ui();
    var section = $("#section").val();
    $.ajax(catsoop.url_root + '/cs_util/api/groups/make_all_groups',
           {method: 'POST',
            data: {'api_token': catsoop.api_token,
                   'path': JSON.stringify(catsoop.path_info),
                   'section': section}}
    ).done(catsoop.update_group_list);
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
    var name = $("#cs_groups_nameadd").val();
    var grp = $("#cs_groups_groupadd").val();
    catsoop.groups_clear_ui();
    var section = $("#section").val();
    $.ajax(catsoop.url_root + '/cs_util/api/groups/add_to_group',
           {method: 'POST',
            data: {'api_token': catsoop.api_token,
                   'path': JSON.stringify(catsoop.path_info),
                   'username': name,
                   'group': grp}}
    ).done(catsoop.update_group_list);
    catsoop.groups_enable_buttons();
}

catsoop.groups_remove = function(name, grp){
    catsoop.groups_clear_ui();
    var section = $("#section").val();
    $.ajax(catsoop.url_root + '/cs_util/api/groups/remove_from_group',
           {method: 'POST',
            data: {'api_token': catsoop.api_token,
                   'path': JSON.stringify(catsoop.path_info),
                   'username': name,
                   'group': grp}}
    ).done(catsoop.update_group_list);
    catsoop.groups_enable_buttons();
}

catsoop.groups_partner = function(){
    var name1 = $("#cs_groups_name1").val();
    var name2 = $("#cs_groups_name2").val();
    catsoop.groups_clear_ui();
    var section = $("#section").val();
    $.ajax(catsoop.url_root + '/cs_util/api/groups/partner',
           {method: 'POST',
            data: {'api_token': catsoop.api_token,
                   'path': JSON.stringify(catsoop.path_info),
                   'username1': name1,
                   'username2': name2}}
    ).done(catsoop.update_group_list);
    catsoop.groups_enable_buttons();
}

$(document).ready(
    function(){
        catsoop.update_group_list();
        $('#section').change(catsoop.update_group_list);
        $('#cs_groups_reassign').click(catsoop.groups_confirm_and_partner_all);
        $('#cs_groups_addtogroup').click(catsoop.groups_add);
        $('#cs_groups_newpartners').click(catsoop.groups_partner);
   });
