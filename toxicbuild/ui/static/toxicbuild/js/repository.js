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


var REPO_ROW_TEMPLATE = `
<tr id="repo-row-{{repo.name}}">
    <td>
	  {{repo.name}}
	  <button type="button" class="btn btn-default btn-xs btn-main-edit
                                       btn-edit-repo"
		  data-toggle="modal" data-target="#repoModal"
		  data-repo-name="{{repo.name}}" data-repo-url="{{repo.url}}"
		  data-repo-update-seconds="{{repo.update_seconds}}"
		  data-repo-vcs-type="{{repo.vcs_type}}"
		  data-repo-id="{{repo.id}}">
	    <span class="glyphicon glyphicon-edit" aria-hidden="true"></span>
	  </button>
	</td>
	<td>{{repo.url}}</td>
	<td>
	  <form action="/waterfall/{{repo.name}}" class="repo-status-form">
	    <button type="submit" class="btn btn-xs btn-pending btn-status" id="btn-status-{{repo.name}}">cloning
	    </button>
	  </form>
          <div class="spinner-placeholder" id="spinner-placeholder-{{repo.name}}">
	    <i class="fa fa-cog fa-spin fa-3x fa-fw toxic-spinner-main" id="spinner-repo-{{repo.name}}"></i>
	  </div>

	</td>
      </tr>

`

var BRANCH_TEMPLATE = `
<div class="form-group repo-branch">
  <h6><label for="repo_branch_name" class="control-label">Branch name: </label>
    <span class="glyphicon glyphicon-remove remove-branch"></span>
  </h6>
  <input type="text" name="branch_name" class="form-control branch-name-input" value="{{repo_branch_name}}"required />
  <input type="checkbox" name="only-latest" class="branch-notify-input" {{checked}}> <span>Only latest commit </span>
</div>
  `


var RepositoryModel = function(attrs){

  var default_attrs = {
    id: null,
    name: null,
    vcs_type: null,
    update_seconds: null,
    branches: null,
    slaves: null,
  }

  var instance_attrs = {};
  jQuery.extend(instance_attrs, default_attrs, attrs);

  // An instance of RepositoryModel
  var instance = {

    createOrUpdate: function(data, success_cb, error_cb){
      // creates a new repo if it does not exists, otherwise updates it.
      var self = this;

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      if (self.id){
	var type = 'put';
      }else{
	var type = 'post';
      }

      var url = '/api/repo/';

      var my_success_cb = function(response){
	// updating instance attributes.
	jQuery.extend(self, data);
	utils.log(response);
	success_cb(response);
      };
      var my_error_cb = function(response){
	utils.log(respose);
	error_cb(respose);
      };

      utils.sendAjax(type, url, data, my_success_cb, my_error_cb);
    },

    addBranch: function(data, success_cb, error_cb){

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'post';
      var url = '/api/repo/add-branch';

      var my_success_cb = function(response){
	utils.log(response);
	success_cb(response);
      }

      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      }

      // false means this will be a sync request.
      utils.sendAjax(type, url, data, my_success_cb, my_error_cb, false);
    },

    removeBranch: function(data, success_cb, error_cb){

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'post';
      var url  = '/api/repo/remove-branch';

      var my_success_cb = function(response){
	utils.log(response);
	success_cb(response);
      }

      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      }
      utils.sendAjax(type, url, data, my_success_cb, my_error_cb);
    },

    delete: function(success_cb, error_cb){
      var self = this;

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'delete';
      var url = '/api/repo/';
      var data = {name: self.name}
      var my_success_cb = function(response){
	utils.log(response);
	success_cb(response);
      };
      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      };

      utils.sendAjax(type, url, data, my_success_cb, my_error_cb);
    },

    startBuild: function(data, success_cb, error_cb){
      // Starts build(s) based on the info of the start build modal.
      var self = this;

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'post';
      var url = '/api/repo/start-build';

      var my_success_cb = function(response){
	utils.log(response);
	success_cb(response);
      };

      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      };

      utils.sendAjax(type, url, data, my_success_cb, my_error_cb);
    },

  }

  jQuery.extend(instance, instance_attrs)
  return instance
}


var RepositoryView = function (model){

  var instance = {
    model: model,
    modal: jQuery('#repoModal'),

    cleanModal: function(){
      // cleans the repository modal.
      var self = this;
      self.modal.find('.modal-title').text('Add repository')
      self.modal.find('#repo_name').val('');
      self.modal.find('#repo_url').val('');
      self.modal.find('#repo_update_seconds').val(300);
      self.modal.find('#repo_vcs_type').val('');
      self.modal.find("#repo_slaves").html('');
      self.modal.find("#btn-delete-repo").hide();
      jQuery('#repo-req-type').val('post');
      jQuery('#branches-container').html('');
    },

    renderModal: function(){
      // sets specifc information about self.model in the modal.
      var self = this;

      if (self.model.id){
	self.modal.find('.modal-title').text(self.model.name);
	self.modal.find('#repo_name').val(self.model.name);
	self.modal.find('#repo_url').val(self.model.url);
	self.modal.find('#repo_update_seconds').val(self.model.update_seconds);
	self.modal.find('#btn-delete-repo').show();

	for (i in self.model.branches){
	  var branch = self.model.branches[i];
	  var template = BRANCH_TEMPLATE.replace('{{repo_branch_name}}',
						 branch.name);
	  var checked = branch.notify_only_latest ? "checked" : "";
	  template = template.replace('{{checked}}', checked);
	  jQuery('#branches-container').append(template);
	}
      };

      var repo_slaves = [];
      for (i in self.model.slaves){
	slave = self.model.slaves[i].name;
	repo_slaves.push(slave);
      };

      for (i in SLAVES){
	var slave = SLAVES[i];
	if (repo_slaves.indexOf(slave) == -1){
	  var selected = "";
	}else{
	  var selected = 'selected';
	};

	var opt = '<option value="' + slave + '"' + selected + '>' + slave + '</option>';
	jQuery(opt).appendTo('#repo_slaves');
      }
    },

    addBranchInModal: function(){
      var template = BRANCH_TEMPLATE.replace('{{repo_branch_name}}', '');
      jQuery('#branches-container').append(template);
    },

    removeBranchFromModal: function(branch_form){
      branch_form.remove();
    },

  }

  return instance
}

var RepositoryManager = {

  views: null,
  modal: jQuery('#repoModal'),
  _current_view: null,
  // modEl not modAl.
  _current_model: null,


  init: function(repositories){
    // instanciates the repositories that will be managed.
    // repositories is an array of objects to be passed
    // to RepositoryModel
    var self = this;

    // {repo.id: view, other_repo.id: other_view, ...}
    self.views = {};
    for (i = 0; i < repositories.length; i++){
      var repo_params = jQuery.parseJSON(repositories[i]);
      var repo = RepositoryModel(repo_params);
      var view = RepositoryView(repo);
      self.views[repo.id] = view;
    }

    self.connect2events();
  },

  connect2events: function(){
    // connecting to submit of the repository modal
    var self = this;

    self.modal.on('submit', function(event){
      // event prevented here means that the form is not valid.
      if (!self._current_view){ throw "No _current_view!"; }

      if (event.isDefaultPrevented()){
	return false;
      }
      event.preventDefault();
      var type = jQuery('#repo-req-type').val();
      if (type == 'delete'){
	self.delete();
      }else{
	self.createOrUpdate();
      }
    });

    //setting repository modal info
    self.modal.on('show.bs.modal', function(event){
      var btn = jQuery(event.relatedTarget);
      var repo_id = btn.data('repo-id');
      self._current_view = self.views[repo_id];
      if (!self._current_view){
	var repo = RepositoryModel();
	var view = RepositoryView(repo);
	self._current_view = view;
      }
      self._current_model = self._current_view.model;
      self._current_view.renderModal();

      // event that triggers the remove of the branch
      jQuery('.remove-branch').on('click', function (){
	var branch_name = jQuery('.branch-name-input',
				 jQuery(this).parent().parent()).val();
	var branch_el = jQuery('.branch-name-input',
			       jQuery(this).parent().parent()).parent();
	self.removeBranch(branch_name, branch_el);
      });

    });

    // cleaning the modal fields after we close it.
    self.modal.on('hidden.bs.modal', function (event) {
      self._current_view.cleanModal();
      self._current_view = null;
      self._current_model = null;
    });

    // validator plugin
    $('#repo-form').validator();

    // adding branch form
    jQuery('.add-branch-icon').on('click', function(){
      self._current_view.addBranchInModal();
      // we need to set it here so remove works with branch forms
      // inserted now.
      jQuery('.remove-branch').on('click', function (){
	var branch_name = jQuery('.branch-name-input',
			       jQuery(this).parent().parent()).val();
	var branch_el = jQuery('.branch-name-input',
			       jQuery(this).parent().parent()).parent();

	self.removeBranch(branch_name, branch_el);
      });
    });

    // changing req-type for delete a repo
    jQuery('#btn-delete-repo').on('click', function(){
      jQuery('#repo-req-type').val('delete');
    });

  },

  getDataFromModal: function(){
    // returns the data from the repository modal
    var self = this;
    var name = self._current_view.modal.find('#repo_name').val();
    var url = self._current_view.modal.find('#repo_url').val();
    var update_seconds = self._current_view.modal.find('#repo_update_seconds').val();
    var vcs_type = self._current_view.modal.find('#repo_vcs_type').val();
    var slaves = [];

    jQuery('#repo_slaves option:selected').each(function(){
      slaves.push(this.value);
    });

    return {'name': name, 'url': url, 'update_seconds': update_seconds,
	    'vcs_type': vcs_type, 'slaves': slaves}
  },

  createOrUpdate: function(){
    var self = this;
    var data = self.getDataFromModal();

    if (self._current_model.id){
      var success_msg = 'Repository updated.'
      var add_row = false;
    }else{
      var success_msg = 'Repository is being created. Please wait.';
      var add_row = true;
    };

    var success_cb = function(response){
      // here we add the branches for the repo.
      var branches = [];
      jQuery('.repo-branch').each(function(){
	var branch_name = jQuery('.branch-name-input', this).val();
	var notify_only_latest = jQuery('.branch-notify-input', this)[0].checked;
	var branch_data = {branch_name: branch_name,
			   notify_only_latest: notify_only_latest,
			   name: self._current_model.name};
	var repo_branch = {name: branch_name, notify_only_latest: notify_only_latest};
	var cb = function(response){utils.log(response)}
	self._current_model.addBranch(branch_data, cb, cb);
	branches.push(repo_branch);
      });
      self._current_model.branches = branches;

      utils.showSuccessMessage(success_msg);
      self.modal.modal('hide');
      if(add_row){
	response = jQuery.parseJSON(response);
	self._insertRepoRow(response)
      };
    };
    var error_cb = function(response){
      utils.showErrorMessage(response)
      self.modal.modal('hide');
    };

    self._current_model.createOrUpdate(data, success_cb, error_cb);
  },

  delete: function(){
    // deletes a repo using data from modal
    var self = this;

    var success_cb = function(response){
      utils.showSuccessMessage('Repository removed.');
      self.modal.modal('hide');
      self._removeRepoRow(self._current_model.name);
    };
    var error_cb = function(response){
      utils.showErrorMessage(response)
      self.modal.modal('hide');
    };

    self._current_model.delete(success_cb, error_cb);
  },

  removeBranch: function(branch_name, branch_el){
    var self = this;

    var type = 'post';
    var url = '/api/repo/remove-branch';
    var data = {name: self._current_model.name,
		branch_name: branch_name};
    success_cb = function(response){
      self._current_view.removeBranchFromModal(branch_el)};

    self._current_model.removeBranch(data, success_cb);
  },

  _insertRepoRow: function(repo){
    var self = this;

    var repo_model = RepositoryModel(repo);
    var view = RepositoryView(repo_model);

    self.views[repo_model.id] = view;

    // inserts a row in the main page for a recently created repo.
    var repo_row = REPO_ROW_TEMPLATE.replace(/{{repo.name}}/g, repo.name);
    repo_row = repo_row.replace(/{{repo.url}}/g, repo.url);
    repo_row = repo_row.replace(/{{repo.vcs_type}}/g, repo.vcs_type);
    repo_row = repo_row.replace(/{{repo.update_seconds}}/g, repo.update_seconds);
    repo_row = repo_row.replace(/{{repo.name}}/g, repo.name);
    repo_row = repo_row.replace(/{{repo.id}}/g, repo.id);
    $('#tbody-repos').append(repo_row);
  },


  _removeRepoRow: function(repo_name){
    jQuery('#repo-row-' + repo_name).remove();
  },

}
