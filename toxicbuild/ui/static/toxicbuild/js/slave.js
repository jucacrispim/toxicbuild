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


var SLAVE_ROW_TEMPLATE = `
<tr id="obj-row-{{slave.id}}">
  <td>
    {{slave.name}}
    <button type="button" class="btn btn-default btn-xs btn-main-edit btn-edit-slave"
	    data-toggle="modal"
	    data-target="#slaveModal"
	    data-obj-id="{{slave.id}}"
	    data-slave-name="{{slave.name}}"
	    data-slave-host="{{slave.host}}"
	    data-slave-port="{{slave.port}}">
      <span class="glyphicon glyphicon-edit" aria-hidden="true"></span>
    </button>
  </td>
  <td>{{slave.host}}</td>
  <td>{{slave.port}}</td>
</tr>

`


var SlaveModel = function (attrs){

  var default_attrs = {
    id: null,
    name: null,
    host: null,
    port: null,
    token: null,
    api_url: '/api/slave/',
  };

  return BaseModel(default_attrs, attrs);
};


var SlaveView = function (model){

  var super_instance = BaseView(model);

  var instance = {
    modal: jQuery('#slaveModal'),

    cleanModal: function(){
      var self = this;
      self.modal.find('.modal-title').text('Add repository');
      self.modal.find('#slave_name').val('');
      self.modal.find('#slave_host').val('');
      self.modal.find('#slave_port').val('');
      self.modal.find("#btn-delete-slave").hide();
      self.modal.find('.req-type').val('post');
    },

    renderModal: function(){
      var self = this;
      utils.log(self.model);
      if (self.model.id){
	self.modal.find('.req-type').val('put');
	self.modal.find('.modal-title').text(self.model.name);
	self.modal.find('#slave_name').val(self.model.name);
	self.modal.find('#slave_host').val(self.model.host);
	self.modal.find('#slave_port').val(self.model.port);
	self.modal.find('#slave_token').val(self.model.token);
	self.modal.find('#btn-delete-slave').show();
      }
    },

    getData: function (){
      var self = this;

      var name = self.modal.find('#slave_name').val();
      var host = self.modal.find('#slave_host').val();
      var port = self.modal.find('#slave_port').val();
      var token = self.modal.find('#slave_token').val();
      return {name: name, port: port, host: host,
	      token: token};
    },

    insertObjRow: function(data){
      var self = this;

      var obj_row = SLAVE_ROW_TEMPLATE.replace(
	  /{{slave.name}}/g, self.model.name);
      obj_row = obj_row.replace(/{{slave.id}}/g, data.id);
      obj_row = obj_row.replace(/{{slave.host}}/g, self.model.host);
      obj_row = obj_row.replace(/{{slave.port}}/g, self.model.port);
      obj_row = obj_row.replace(/{{slave.token}}/g, self.model.token);
      $('#tbody-slaves').append(obj_row);
    },
  };

  var inherited = {};
  jQuery.extend(inherited, super_instance, instance);
  return inherited;
};


var _SlaveManager = function (){
  var modal = jQuery('#slaveModal')
  var super_instance =  BaseManager(SlaveModel, SlaveView, modal);
  var inherited = {};

  var instance = {
    init: function(model_confs){
      var self = inherited;
      super_instance.init(self, model_confs);
      super_instance.modal = self.modal;
      super_instance.views = self.views
    },

    delete: function(){
      var self = inherited;
      success_msg = 'Slave removed';
      super_instance._current_view = self._current_view;
      super_instance._current_model = self._current_model;

      success_cb = function(response){
	SLAVES.splice(SLAVES.indexOf(self._current_model.name), 1);
      }
      super_instance.delete(success_msg, success_cb);
    },

    createOrUpdate: function(){
      var self = inherited;
      update_success_msg = 'Slave updated';
      create_success_msg = 'Slave created';

      super_instance._current_view = self._current_view;
      super_instance._current_model = self._current_model;

      success_cb = function(response){
	SLAVES.push(self._current_model.name);
      }

      super_instance.createOrUpdate(update_success_msg, create_success_msg,
				    success_cb);

    },
  };

  jQuery.extend(inherited, super_instance, instance);
  return inherited;
};

var SlaveManager = _SlaveManager();
