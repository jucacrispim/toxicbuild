// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

// This file is part of toxicbuild.

// toxicbuild is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// toxicbuild is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.


function StreamConsumer(){
  obj = {
    url: 'ws://' + window.location.host + '/api/socks/repo-status',
    ws: null,

    init: function(){
      var self = this;
      self.ws = new WebSocket(self.url);
      self.ws.onmessage = function(event){
	self.handle_ws_info(event);
      };
    },

    handle_ws_info: function(event){
      var self = this;
      var data = jQuery.parseJSON(event.data);
      e_type = data['event_type']
      utils.log(e_type);
      if (e_type == 'repo_status_changed'){
	self.change_repo_status(data);
      }else if (e_type == 'repo_added'){
	RepositoryManager._insertRepoRow(data);
      };
    },

    change_repo_status: function(data){
      var self = this;
      var statuses = {'success': 'success', 'fail': 'danger',
                      'running': 'info', 'exception': 'exception',
                      'clone-exception': 'exception',
		      'ready': 'success',
                      'warning': 'warning',
                      'cloning': 'pending'}

      var status = data.status;
      var new_class = 'btn-' + statuses[status];
      var btn = jQuery('#btn-status-' + data.name);
      var old_status = data.old_status;
      var old_class = 'btn-' + statuses[old_status];

      // animate class transition
      var transition_time = 200; // ms
      btn.animate({
	opacity: 0.8

      }, transition_time, function(){
	btn.removeClass(old_class);
	btn.removeClass('btn-pending');
	btn.addClass(new_class);
	btn.text(status);
	btn.animate({opacity: 1}, transition_time)});

      if (status == 'running'){
	jQuery('#spinner-repo-' + data.name).fadeIn();
      }else{
	jQuery('#spinner-repo-' + data.name).fadeOut();
      }
    }
  };

  obj.init();
  return obj;
}

var consumer = StreamConsumer()
