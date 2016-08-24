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
<tr id="row-{{repo.name}}">
  <td>
    <button type="button" class="btn btn-toxicbuild-default btn-xs"
            data-toggle="modal" data-target="#repoModal"
            data-repo-name="{{repo.name}}" data-repo-url="{{repo.url}}"
            data-repo-update-seconds="{{repo.update_seconds}}"
            data-repo-vcs-type="{{repo.vcs_type}}">
      {{repo.name}}
    </button>
  </td>
  <td>{{repo.url}}</td>
  <td>
    <form action="/waterfall/{{repo.name}}">
      <button type="submit" class="btn btn-xs btn-pending btn-status">
        cloning
      </button>
    </form>
  </td>
</tr>
  `

var BRANCH_TEMPLATE = `
<div class="form-group">
  <h6><label for="repo_branch_name" class="control-label">Branch name: </label>
    <span class="glyphicon glyphicon-remove remove-branch"></span>
  </h6>
  <input type="text" name="branch_name" id="branch_name" class="form-control branch-name-input" required />
  <input type="checkbox" aria-label="..."> <span>Only latest commit </span>
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

  var instance_attrs = {}
  jQuery.extend(instance_attrs, default_attrs, attrs)

  // An instance of RepositoryModel
  var instance = {

    createOrUpdate: function(data, success_cb, error_cb){
      // creates a new repo if it does not exists, otherwise updates it.
      var self = this;

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      if (self.id){
	var type = 'put'
      }else{
	var type = 'post'
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
      self.modal.find("#btn-delete-repo").hide();
      jQuery('#repo-req-type').val('post');
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
      }
    },

    addBranchInModal: function(){
      jQuery('#branches-container').append(BRANCH_TEMPLATE);
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
      var repo_params = repositories[i];
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
      // inserted via js
      jQuery('.remove-branch').on('click', function (){
	self._current_view.removeBranchFromModal(jQuery(this).parent().parent());
      });
    });

    // remove branch
    jQuery('.remove-branch').on('click', function (){
      self._current_view.removeBranchFromModal(jQuery(this).parent().parent());
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

  _insertRepoRow: function(repo){
    // inserts a row in the main page for a recently created repo.

    var repo_row = REPO_ROW_TEMPLATE.replace(/{{repo.name}}/g, repo.name);
    repo_row = repo_row.replace(/{{repo.url}}/g, repo.url);
    repo_row = repo_row.replace(/{{repo.vcs_type}}/g, repo.vcs_type);
    repo_row = repo_row.replace(/{{repo.update_seconds}}/g, repo.update_seconds);
    $('#tbody-repos').append(repo_row);
  },

  createOrUpdate: function(){
    var self = this;
    var data = self.getDataFromModal();

    var success_cb = function(response){
      utils.showSuccessMessage(
	'Repository is being created. Please wait.');
      self.modal.modal('hide');
      self._insertRepoRow(data);
    };
    var error_cb = function(response){
      utils.showErrorMessage(response)
      self.modal.modal('hide');
    };

    self._current_model.createOrUpdate(data, success_cb, error_cb);
  },

  _removeRepoRow: function(repo_name){
    jQuery('#repo-row-' + repo_name).remove();
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
}

//     getStartBuildInfo: function(){
//       var repo_name = $('#start_build_name').val()
//       var branch = $('#branch').val();
//       var builder_name = $('#builder_name').val();
//       var named_tree = $('#named_tree').val();
//       var slaves = new Array();
//       jQuery('#repo_slaves option:selected').each(function(){
// 	slaves.push(this.value);
//       });

//       var kwargs = {'branch': branch, 'name': repo_name};
//       if (builder_name){
// 	kwargs['builder_name'] = builder_name;
//       }
//       if(named_tree){
// 	kwargs['named_tree'] = named_tree;
//       }
//       if (slaves){
// 	kwargs['slaves'] = slaves;
//       }
//       return kwargs;
//     },

//     startBuild: function(){
//       // Starts build(s) based on the info of the start build modal.
//       var self = this;

//       var data = self.getStartBuildInfo();
//       var type = 'post';
//       var url = '/api/repo/start-build';

//       var success_cb = function(response){
// 	utils.showSuccessMessage(response);
// 	self.start_build_modal.modal('hide');
//       };

//       var error_cb = function(response){
// 	utils.showErrorMessage(response);
// 	self.start_build_modal.modal('hide');
//       };

//       utils.sendAjax(type, url, data, success_cb, error_cb);
//     },

//     addBranchForm: function(){
//       var branch_template = BRANCH_FORM_TEMPLATE.join('');
//       jQuery('#branches-container').append(branch_template);
//     },

//     removeBranchForm: function(branch_form){
//       branch_form.remove();
//     }
//   };

//   // validator plugin
//   $('#repo-form').validator();

//   // cleaning the modal fields after we close it.
//   obj.modal.on('hidden.bs.modal', function (event) {
//     obj.cleanModal();
//   });

//   //setting repository modal info
//   obj.modal.on('show.bs.modal', function(event){
//     var btn = jQuery(event.relatedTarget);
//     obj.setRepoInfo(btn);
//   });

//   // setting repo name for start build
//   obj.start_build_modal.on('show.bs.modal', function(event){
//     var btn = jQuery(event.relatedTarget);
//     $('#repo-start-build-name').val($(this).data('repo-name'));
//   });

//   // changing req-type for delete a repo
//   jQuery('#btn-delete-repo').on('click', function(){
//     $('#repo-req-type').val('delete');
//   });


//   // adding branch form
//   jQuery('.add-branch-icon').on('click', function(){
//     obj.addBranchForm();

//     // we need to set it here so remove works with branch forms
//     // inserted via js
//     jQuery('.remove-branch').on('click', function (){
//       obj.removeBranchForm(jQuery(this).parent().parent());
//     });

//   });

//   // remove branch
//   jQuery('.remove-branch').on('click', function (){
//     obj.removeBranchForm(jQuery(this).parent().parent());
//   });

//   // connecting to submit of the removeBranchFormpository modal
//   obj.modal.on('submit', function(event){
//     // event prevented here means that the form is not valid.
//     if (event.isDefaultPrevented()){
//       return false;
//     }

//     event.preventDefault();
//     var type = jQuery('#repo-req-type').val();
//     if (type == 'delete'){
//       obj.delete();
//     }
//     else if (type == 'post'){
//       obj.create();
//     }
//     else{
//       obj.update();
//     }

//   });

//   // setting repo name for start build
//   $('.start-build-btn').on('click', function(event){
//     $('#start_build_name').val($(this).data('start-build-name'));
//   });


//   // connecting to start build modal submit
//   jQuery('#startBuildModal').on('submit', function(event){
//     // event prevented here means that the form is not valid.
//     if (event.isDefaultPrevented()){
//       return false;
//     }

//     event.preventDefault();
//     obj.startBuild();
//   });

//   return obj;
// };
