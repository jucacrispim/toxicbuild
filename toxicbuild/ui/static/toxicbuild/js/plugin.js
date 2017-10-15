// Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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


var PLUGIN_TEMPLATE = `
<div class="plugin-container" id="plugin-container-{{PLUGIN-NAME}}">
  <input type="hidden" value="{{PLUGIN-NAME}}" class="plugin-name-input" name="plugin_name">

  <span class="plugin-name">
    <img src="/static/toxicbuild/img/{{PLUGIN-NAME}}.png"/>
    {{PLUGIN-NAME}}
      <span class="glyphicon glyphicon-triangle-left plugin-config-glyphicon"
            aria-hidden="true"></span>
  </span>

  <div class="enable-plugin-container">
    <div class="enable-plugin-label">Enabled</div>
    <div class="enable-plugin-input">
    <input type="checkbox" class="form-control" {{CHECKED}}>
    </div>
  </div>
  <div class="plugin-attrs-container" style="display:none">{{PLUGIN-ATTRS}}</div>
</div>
`

var PluginModel = function(attrs){

  var default_attrs = {
    name: null,
    fields: [],
  }

  var instance_attrs = {};
  jQuery.extend(instance_attrs, default_attrs, attrs);

  // An instance of PluginModel
  var instance = {

    list: function(data, success_cb, error_cb){

      success_cb = success_cb || function(response){return false};
      error_cb = error_cb || function(response){return false};

      var type = 'get';
      var url = '/api/repo/list-plugins';

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
  jQuery.extend(instance, instance_attrs);
  return instance
}


var PluginView = function(model){

  var instance = {
    model: model,
    modal: jQuery('#outputPluginModal'),

    cleanModal: function(){
      // cleans the repository modal.
      jQuery('#plugins-container').html('');
    },

    renderModal: function(repo){
      // sets specifc information about self.model in the modal.
      var self = this;

      var template = PLUGIN_TEMPLATE.replace(/{{PLUGIN-NAME}}/g,
					     self.model.name);

      var plugin_attrs = '';
      plugin = repo.hasPlugin(self.model.name)
      checked = plugin ? "checked" : "";
      jQuery.each(self.model, function(key, value){
	var bad_attrs = ['name', 'list', 'type', 'fields']
	if (bad_attrs.indexOf(key) >= 0){
	  // continue
	  return 1
	}
	var val = checked ? plugin[key] : "";
	var label = '<label for="" class="control-label">'+ key + '</label>';
	plugin_attrs += '<br/>' + label +
	  '<input type="text" class="form-control" name="' + key + '"' +
	  'value="' + val + '"/>'
      });
      template = template.replace(/{{PLUGIN-ATTRS}}/, plugin_attrs);
      template = template.replace(/{{CHECKED}}/, checked);

      template = jQuery(template);
      jQuery('.glyphicon', template).on('click', function(){
	var plugin_container = jQuery(this).parent().parent();
	self.showConfigs(plugin_container, jQuery(this));
      });
      jQuery('#plugins-container').append(template);
    },

    showConfigs: function(plugin_container, glyph){
      attrs = jQuery('.plugin-attrs-container', plugin_container);
      if (glyph.hasClass('glyphicon-triangle-left')){
	glyph.removeClass('glyphicon-triangle-left').addClass(
	  'glyphicon-triangle-bottom')
      }else{
	glyph.removeClass('glyphicon-triangle-bottom').addClass(
	  'glyphicon-triangle-left')
      }
      attrs.toggle(300);
      //self.
    }
  }
  return instance;
};

var PluginManager = {

  views: null,
  modal: jQuery('#outputPluginModal'),
  _current_view: null,
  _current_model: null,
  _current_repo: null,
  _to_enable: [],
  _to_disable: [],

  init: function(plugins){
    var self = this;

    self.views = {};
    for (i = 0; i < plugins.length; i++){
      var plugin_params = jQuery.parseJSON(plugins[i]);
      var plugin = PluginModel(plugin_params);
      var view = PluginView(plugin);
      self.views[plugin.name] = view;
    }

    self.connect2events();
  },

  connect2events: function(){
    // connecting to submit of the repository modal
    var self = this;

    //setting repository modal info
    self.modal.on('show.bs.modal', function(event){
      var btn = jQuery(event.relatedTarget);

      var repo = RepositoryManager.getRepoById(btn.data('repo-id'));
      self._current_repo = repo;

      jQuery.each(self.views, function(name, view){
	view.renderModal(self._current_repo);
	self.connectChecboxEvents();
      });

    });
    self.modal.on('hidden.bs.modal', function (event) {
      jQuery.each(self.views, function(key, value){
	value.cleanModal();
      });
      self._current_repo = null;
    });

    jQuery('#btn-save-plugins').on('click', function(){
      var btn = jQuery(this);

      jQuery.each(self._to_disable, function(i, plugin_name){
	container = jQuery('#plugin-container-' + plugin_name);
	var plugin_name = jQuery('input[type=hidden]', container)[0].value;
	var data = {'name': self._current_repo.name,
		    'plugin_name': plugin_name};

	self._current_repo.rmFromPluginList(plugin_name);
	success_msg = 'Plugin '+ plugin_name +' disabled';
	error_msg = 'Error disabling '+ plugin_name + ' plugin';
	self._current_repo.disablePlugin(data,
					 utils.showSuccessMessage(success_msg),
					 utils.showErrorMessage(error_msg));
	self.modal.modal('hide');
      });
      self._to_disable = [];

      jQuery.each(self._to_enable, function(i, plugin_name){
	container = jQuery('#plugin-container-' + plugin_name);
	var plugin_name = jQuery('input[type=hidden]', container)[0].value;
	var data = self.getPluginData(container);
	success_msg = 'Plugin '+ plugin_name +' enabled';
	error_msg = 'Error enabling '+ plugin_name + ' plugin';

	self._current_repo.enablePlugin(data,
					utils.showSuccessMessage(success_msg),
					utils.showErrorMessage(error_msg));
	plugin = jQuery.extend(data, {'name': plugin_name});
	utils.log(plugin);
	self._current_repo.add2PluginList(plugin);
	self.modal.modal('hide');
      });
      self._to_enable = [];

    });
  },

  connectChecboxEvents: function(){
    self = this;

    jQuery.each(jQuery('input[type=checkbox]'), function(i, el){
      var el = jQuery(el);
      el.on('click', function(){
	var chk = jQuery(this);
	var container = chk.parent().parent().parent();
	var plugin_name = jQuery('input[type=hidden]', container)[0].value;
	var checked = chk.context.checked;
	if (checked && self._to_disable.indexOf(plugin_name) < 0){
	  self._to_enable.push(plugin_name);
	}else if(checked && self._to_disable.indexOf(plugin_name) >= 0){
	  var index = self._to_disable.indexOf(plugin_name);
	  self._to_disable.splice(index, 1)
	}else if (!checked && self._to_enable.indexOf(plugin_name) < 0){
	  self._to_disable.push(plugin_name);
	}else{
	  index = self._to_enable.indexOf(plugin_name);
	  self._to_enable.splice(index, 1);
	}
	utils.log('enable: ' + self._to_enable);
	utils.log('disable: ' + self._to_disable);
      });
    });
  },

  getPluginData: function(container){
    var self = this;

    var data = {};
    jQuery.each(jQuery('input', container), function(i, el){
      if (el.type != 'checkbox' || el.name){
	data[el.name] = el.value;
      };
    });
    data['name'] = self._current_repo.name;
    utils.log(data);
    return data;
  },

}
