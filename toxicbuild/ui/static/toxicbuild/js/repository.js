// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

// This file is part of toxicbuild.

// toxicbuild is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// toxicbuild is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.


var REPO_ROW_TEMPLATE = [
  '<tr id="row-{{repo.name}}">',
    '<td>',
      '<button type="button" class="btn btn-toxicbuild-default btn-xs"',
              'data-toggle="modal" data-target="#repoModal"',
              'data-repo-name="{{repo.name}}" data-repo-url="{{repo.url}}"',
              'data-repo-update-seconds="{{repo.update_seconds}}"',
              'data-repo-vcs-type="{{repo.vcs_type}}">',
        '{{repo.name}}',
      '</button>',
    '</td>',
    '<td>{{repo.url}}</td>',
    '<td>',
      '<form action="/waterfall">',
        '<input type="hidden" name="repo" value="{{repo.name}}">',
        '<button type="submit" class="btn btn-xs btn-{{repo.status}} btn-status">',
          '{{repo.status}}',
        '</button>',
      '</form>',
    '</td>',
    '<td>',
      '<button type="button" class="btn btn-xs btn-toxicbuild-default"',
              'data-toggle="modal" data-repo-name="{{repo.name}}"',
              'data-target="#startBuildModal">start build</button>',
    '</td>',
  '</tr>',
];


var RepositoryManager = function(){
  // the main repository manager object
  var obj = {
    modal: jQuery('#repoModal'),
    start_build_modal: jQuery('#startBuildModal'),

    cleanModal: function(){
      // cleans the repository modal.
      var self = this;
      var modal = self.modal;
      modal.find('.modal-title').text('Add repository')
      modal.find('#repo_name').val('');
      modal.find('#repo_url').val('');
      modal.find('#repo_update_seconds').val(300);
      modal.find('#repo_vcs_type').val('');
      modal.find("#btn-delete-repo").hide();
    },

    setRepoInfo: function(btn){
      // sets the repository info in the modal.

      var self = this;

      var name = btn.data('repo-name');
      var url = btn.data('repo-url');
      var update_seconds = btn.data('repo-update-seconds');
      var vcs_type = btn.data('repo-vcs-type');

      if (url){
	self.modal.find('#repo-req-type').val('put');
	self.modal.find('#btn-delete-repo').show();
      }
      else{
	self.modal.find('#repo-req-type').val('post');
	self.modal.find('#btn-delete-repo').hide();
      }

      self.modal.find('.modal-title').text(name);
      self.modal.find('#repo_name').val(name);
      self.modal.find('#repo_url').val(url);
      self.modal.find('#repo_update_seconds').val(update_seconds);
    },

    getRepoInfo: function(){
      // returns the data of the repository modal
      var self = this;
      var modal = self.modal;
      var name = modal.find('#repo_name').val();
      var url = modal.find('#repo_url').val();
      var update_seconds = modal.find('#repo_update_seconds').val();
      var vcs_type = modal.find('#repo_vcs_type').val();
      var slaves = new Array();
      jQuery('#repo_slaves option:selected').each(function(){
	slaves.push(this.value);
      });
      return {'name': name, 'url': url, 'update_seconds': update_seconds,
	      'vcs_type': vcs_type, 'slaves': slaves}
    },

    insertRepoRow: function(name, url, vcs_type, update_seconds, slaves){
      // Insert a row in the table of repositories.
      var repo_row = REPO_ROW_TEMPLATE.join('').replace(/{{repo.name}}/g, name);
      repo_row = repo_row.replace(/{{repo.url}}/g, url);
      repo_row = repo_row.replace(/{{repo.vcs_type}}/g, vcs_type);
      repo_row = repo_row.replace(/{{repo.update_seconds}}/g, update_seconds);
      repo_row = repo_row.replace(/{{[s.name for s in repo.slaves]}}/g,
				  str(slaves));
      $('#tbody-repos').append(repo_row);

    },

    removeRepoRow: function(name){
      // removes a row from the repositories' table.
      jQuery('#repo-row-' + name).remove();
    },

    create: function(){
      // creates a new repo using data from modal
      var self = this;

      var type = 'post';
      var url = '/api/repo/';
      var data = self.getRepoInfo();

      var success_cb = function(response){
	utils.showSuccessMessage(
	  'Repository is being created. Please wait.');
	self.modal.modal('hide');
	self.insertRepoRow(data.name, data.url, data.vcs_type,
			   data.update_seconds, data.slaves);
      };
      var error_cb = function(response){
	utils.showErrorMessage(response)
	self.modal.modal('hide');
      };

      utils.sendAjax(type, url, data, success_cb, error_cb)
    },

    delete: function(){
      // deletes a repo using data from modal
      var self = this;

      var type = 'delete';
      var url = '/api/repo/';
      var data = self.getRepoInfo();

      var success_cb = function(response){
	utils.showSuccessMessage('Repository removed.');
	self.modal.modal('hide');
	self.removeRepoRow(data.name);
      };
      var error_cb = function(response){
	utils.showErrorMessage(response)
	self.modal.modal('hide');
      };

      utils.sendAjax(type, url, data, success_cb, error_cb)
    },

    update: function(){
      // updates a repo using data from modal
      var self = this;

      var type = 'put';
      var url = '/api/repo/';
      var data = self.getRepoInfo();

      var success_cb = function(response){
	utils.showSuccessMessage('Repository updated');
	self.modal.modal('hide');
      };
      var error_cb = function(response){
	utils.showErrorMessage(response)
	self.modal.modal('hide');
      };

      utils.sendAjax(type, url, data, success_cb, error_cb)
    },

    getStartBuildInfo: function(){
      var repo_name = $('#repo-start-build-name').val()
      var branch = $('#branch').val();
      var builder_name = $('#builder_name').val();
      var named_tree = $('#named_tree').val();
      var slaves = new Array();
      jQuery('#repo_slaves option:selected').each(function(){
	slaves.push(this.value);
      });

      var kwargs = {'branch': branch, 'name': repo_name};
      if (builder_name){
	kwargs['builder_name'] = builder_name;
      }
      if(named_tree){
	kwargs['named_tree'] = named_tree;
      }
      if (slaves){
	kwargs['slaves'] = slaves;
      }
      return kwargs;
    },

    startBuild: function(){
      // Starts build(s) based on the info of the start build modal.
      var self = this;

      var data = self.getStartBuildInfo();
      var type = 'post';
      var url = '/api/repo/start-build';

      var success_cb = function(response){
	utils.showSuccessMessage(response);
	self.start_build_modal.modal('hide');
      };

      var error_cb = function(response){
	utils.showErrorMessage(response);
	self.start_build_modal.modal('hide');
      };

      utils.sendAjax(type, url, data, success_cb, error_cb);
    },
  };

  // validator plugin
  $('#repo-form').validator();

  // cleaning the modal fields after we close it.
  obj.modal.on('hidden.bs.modal', function (event) {
    obj.cleanModal();
  });

  //setting repository modal info
  obj.modal.on('show.bs.modal', function(event){
    var btn = jQuery(event.relatedTarget);
    obj.setRepoInfo(btn);
  });

  // setting repo name for start build
  obj.start_build_modal.on('show.bs.modal', function(event){
    var btn = jQuery(event.relatedTarget);
    $('#repo-start-build-name').val($(this).data('repo-name'));
  });

  // changing req-type for delete a repo
  jQuery('#btn-delete-repo').on('click', function(){
    $('#repo-req-type').val('delete');
  });

  // connecting to submit of the repository modal
  obj.modal.on('submit', function(event){
    // event prevented here means that the form is not valid.
    if (event.isDefaultPrevented()){
      return false;
    }

    event.preventDefault();
    var type = jQuery('#repo-req-type').val();
    if (type == 'delete'){
      obj.delete();
    }
    else if (type == 'post'){
      obj.create();
    }
    else{
      obj.update();
    }

  });

  // connecting to start build modal submit
  jQuery('#startBuildModal').on('submit', function(event){
    // event prevented here means that the form is not valid.
    if (event.isDefaultPrevented()){
      return false;
    }

    event.preventDefault();
    obj.startBuild();
  });

  return obj;
};
