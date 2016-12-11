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


var BaseModel = function (default_attrs, attrs){

  var instance_attrs = {};

  jQuery.extend(instance_attrs, default_attrs, attrs);

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

      var my_success_cb = function(response){
	// updating instance attributes.
	jQuery.extend(self, data);
	utils.log(response);
	success_cb(response);
      };
      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      };

      utils.sendAjax(type, self.api_url, data, my_success_cb, my_error_cb);
    },

    delete: function(success_cb, error_cb){
      var self = this;

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'delete';
      var data = {name: self.name}
      var my_success_cb = function(response){
	utils.log(response);
	success_cb(response);
      };
      var my_error_cb = function(response){
	utils.log(response);
	error_cb(response);
      };

      utils.sendAjax(type, self.api_url, data, my_success_cb, my_error_cb);
    },
  };
  jQuery.extend(instance, instance_attrs);
  return instance;
};


var BaseView = function(model){

  var instance = {
    model: model,
    modal: null,

    removeObjRow: function(obj_id){
      jQuery('#obj-row-' + obj_id).remove();
    },
  };

  return instance;
};


var BaseManager = function(model_type, view_type, modal){
  var instance = {

    views: null,
    modal: modal,
    model_type: model_type,
    view_type: view_type,
    _current_view: null,
    _current_model: null,


    init: function(self, model_confs){
      // instanciates the models that will be managed.
      // model_type is the model that will be instanciated
      // view_type is the view that will be instanciated with the model
      // model_confs is an array of objects to be passed
      // to model_type
      self.model_type = model_type;
      self.view_type = view_type;

      // {model.id: view, other_model.id: other_view, ...}
      self.views = {};
      for (i = 0; i < model_confs.length; i++){
	var model_params = jQuery.parseJSON(model_confs[i]);
	var model = model_type(model_params);
	var view = view_type(model);
	self.views[model.id] = view;
      }
      self.connect2events();
    },

    connect2events: function(){
      var self = this;
      // changing req-type for delete a obj
      self.modal.find('#btn-delete-slave').on('click', function(){
	self.modal.find('.req-type').val('delete');
      });

      // connecting to submit of the modal
      self.modal.on('submit', function(event){
	// event prevented here means that the form is not valid.
	if (!self._current_view){ throw "No _current_view!"; }

	if (event.isDefaultPrevented()){
	  return false;
	}
	event.preventDefault();
	var type = self.modal.find('.req-type').val();
	if (type == 'delete'){
	  self.delete();
	}else{
	  self.createOrUpdate();
	}
      });

      //setting repository modal info
      self.modal.on('show.bs.modal', function(event){
	var btn = jQuery(event.relatedTarget);
	var model_id = btn.data('obj-id');
	self._current_view = self.views[model_id];
	if (!self._current_view){
	  var model = self.model_type();
	  var view = self.view_type(model);
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
      self.modal.find('.obj-form').validator();

    },

    delete: function(success_msg, success_cb){
      // deletes a repo using data from modal
      var self = this;

      var my_success_cb = function(response){
	success_cb(response);
	utils.showSuccessMessage(success_msg);
	self.modal.modal('hide');
	self._current_view.removeObjRow(self._current_model.id);
	delete self.views[self._current_model.id]
      };

      var error_cb = function(response){
	utils.showErrorMessage(response)
	self.modal.modal('hide');
      };
      self._current_model.delete(my_success_cb, error_cb);
    },

    createOrUpdate: function(update_success_msg, create_success_msg,
			     success_cb, error_cb){
      var self = this;
      var data = self._current_view.getData();

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      if (self._current_model.id){
	var success_msg = update_success_msg;
	var add_row = false;
      }else{
	var success_msg = create_success_msg;
	var add_row = true;
      };

      var my_success_cb = function(response){
	success_cb(response);
	utils.showSuccessMessage(success_msg);
	self.modal.modal('hide');
	self._current_model.id = JSON.parse(response).id;
	self._current_view.model = self._current_model
	self.views[self._current_model.id] = self._current_view
	if(add_row){self._current_view.insertObjRow(self._current_model)};
      }

      var my_error_cb = function(response){
	error_cb(response);
	utils.showErrorMessage(response);
	self.modal.modal('hide');
      };

      self._current_model.createOrUpdate(data, my_success_cb, my_error_cb);
    },

  };

  return instance
};
