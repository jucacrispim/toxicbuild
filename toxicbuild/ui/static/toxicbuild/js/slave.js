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


var SLAVE_ROW_TEMPLATE = [
  '<tr id="slave-row-{{slave.name}}">',
    '<td>',
      '<button type="button" class="btn btn-toxicbuild-default btn-xs"',
              'data-toggle="modal"',
              'data-target="#slaveModal"',
              'data-slave-name="{{slave.name}}"',
              'data-slave-host="{{slave.host}}"',
              'data-slave-port="{{slave.port}}">',
        '{{slave.name}}',
      '</button>',
    '</td>',
    '<td>{{slave.host}}</td>',
    '<td>{{slave.port}}</td>',
  '</tr>',
];


var SlaveManager = function(){
  // the main repository manager object
  var obj = {
    modal: jQuery('#slaveModal'),

    cleanModal: function(){
      // cleans the slave modal.
      var self = this;
      var modal = self.modal;
      modal.find('.modal-title').text('Add slave')
      modal.find('#slave_name').val('');
      modal.find('#slave_host').val('');
      modal.find('#slave_port').val('');
      modal.find("#btn-delete-slave").hide();
    },

    setSlaveInfo: function(btn){
      // sets the slave info in the modal.
      var self = this;

      var name = btn.data('slave-name');
      var host = btn.data('slave-host');
      var port = btn.data('slave-port');

      if (host){
	self.modal.find('#slave-req-type').val('put');
	self.modal.find('#btn-delete-slave').show();
      }
      else{
	self.modal.find('#slave-req-type').val('post');
	self.modal.find('#btn-delete-slave').hide();
      }

      self.modal.find('.modal-title').text(name);
      self.modal.find('#slave_name').val(name);
      self.modal.find('#slave_host').val(host);
      self.modal.find('#slave_port').val(port);

    },

    getSlaveInfo: function(){
      // returns the data of the repository modal
      var self = this;
      var modal = self.modal;
      var name = modal.find('#slave_name').val();
      var host = modal.find('#slave_host').val();
      var port = modal.find('#slave_port').val();
      return {'name': name, 'host': host, 'port': port}
    },

    insertSlaveRow: function(name, host, port){
      var slave_row = SLAVE_ROW_TEMPLATE.join('').replace(
	  /{{slave.name}}/g, name);
      slave_row = slave_row.replace(/{{slave.host}}/g, host);
      slave_row = slave_row.replace(/{{slave.port}}/g, port);
      $('#tbody-slaves').append(slave_row);
    },

    removeSlaveRow: function(name){
      jQuery('#slave-row' + name).remove();
    },

    create: function(){
      // creates a new repo using data from modal
      var self = this;

      var type = 'post';
      var url = '/api/slave/';
      var data = self.getSlaveInfo();

      var success_cb = function(response){
	utils.showSuccessMessage('Slave created');
	self.modal.modal('hide');
	self.insertSlaveRow(data.name, data.host, data.port);
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
      var url = '/api/slave/';
      var data = self.getSlaveInfo();

      var success_cb = function(response){
	utils.showSuccessMessage('Slave removed.');
	self.modal.modal('hide');
	self.removeSlaveRow(data.name);
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
      var url = '/api/slave/';
      var data = self.getRepoInfo();

      var success_cb = function(response){
	utils.showSuccessMessage('Slave updated');
	self.modal.modal('hide');
      };
      var error_cb = function(response){
	utils.showErrorMessage(response)
	self.modal.modal('hide');
      };

      utils.sendAjax(type, url, data, success_cb, error_cb)
    },
  };

  // validator plugin
  $('#slave-form').validator();

  // cleaning the modal fields after we close it.
  obj.modal.on('hidden.bs.modal', function (event) {
    obj.cleanModal();
  });

  //setting repository modal info
  obj.modal.on('show.bs.modal', function(event){
    var btn = jQuery(event.relatedTarget);
    obj.setSlaveInfo(btn);
  });

  // changing req-type for delete a slave
  jQuery('#btn-delete-slave').on('click', function(){
    $('#slave-req-type').val('delete');
  });

  // connecting to submit of the repository modal
  obj.modal.on('submit', function(event){
    // event prevented here means that the form is not valid.
    if (event.isDefaultPrevented()){
      return false;
    }

    event.preventDefault();
    var type = jQuery('#slave-req-type').val();
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

  return obj
};
