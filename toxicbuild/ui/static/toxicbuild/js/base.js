// Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

function _get_url(method, obj){
  let url = obj._api_url;
  if (method == 'delete' || method == 'update' || method == 'read'){
    if (!obj._query){
      url += '?id=' + obj.id;
    }else{
      url += '?' + Object.keys(obj._query)[0] + '=' + Object.values(
	obj._query)[0];
    }
  }
  return url;
};

async function is_name_available(model, name){
  var r;
  try{
    r = await model.fetch({'name': name});
    r = model.parse(r);
  }catch(e){
    r = null;
  }
  return !Boolean(r);
}

function _getHeaders(){
  let xsrf_token = Cookies.get('_xsrf');
  let headers = {'X-XSRFToken': xsrf_token};
  return headers;
}

class BaseModel extends Backbone.Model{

  constructor(attributes, options){
    super(attributes, options);
    this._init_values = attributes || {};
    this._changes = {};
  }

  _getHeaders(){
    return _getHeaders();
  }

  async _request2api(method, url, body){
    let headers = this._getHeaders();
    let resp = await $.ajax(
      {'url': url, 'data': JSON.stringify(body), 'type': method,
       'contentType': "application/json", 'headers': headers});

    return resp;
  }

  async _post2api(url, body){
    let r = await this._request2api('post', url, body);
    return r;
  }

  sync(method, model, options){
    let url = _get_url(method, this, false);
    options.url = url;
    let headers = this._getHeaders();
    options.headers = headers;
    return super.sync(method, model, options);
  }

  parse(data){
    if (data.items){
      data =  data.items[0];
    }
    return data;
  }

  fetch(options){
    this._query = options;
    let r = super.fetch(options);
    this._has_used_query = true;
    delete this._query;
    return r;
  }

  set(key, value, options){
    this._changes = this._changes || {};
    super.set(key, value, options);
    let init_values = this._init_values || {};
    let init = init_values[key];
    if (value != init){
      this._changes[key] = value;
    }else{
      delete this._changes[key];
    }
  }

  async remove(){
    let url = this._api_url + '?id=' + this.id;
    let headers = this._getHeaders();
    await $.ajax({'url': url, 'type': 'delete',
		  'headers': headers});
  }
}


class BaseCollection extends Backbone.Collection{

  parse(data){
    data = data.items;
    return data;
  }

  sync(method, model, options){
    options.headers = _getHeaders();
    let r = super.sync(method, model, options);
    return r;
  }
}


class BaseFormView extends Backbone.View{

  constructor(options){
    options = options || {};
    super(options);
    this.model = options.model || null;
    this._model_init_values = {};
    this._model_changed = {};

    this._name_avail_s = '#obj-name-available #available-text';
    this._name_avail_indicator_s = '#obj-name-available .check-error-indicator';
    this._name_avail_spinner_s = '.wait-name-available-spinner';
    this._name_available = null;
    this._name_available_indicator = null;
    this._name_available_spinner = null;

    this._save_btn = $('.save-btn-container button');
    this._save_btn_text = $(
      '.obj-details-buttons-container #save-obj-btn-text');
    this._save_btn_spinner = $(
      '.obj-details-buttons-container #save-obj-btn-spinner');

  }

  _getChangesFromInput(){
    let self = this;

    $('input').each(function(){
      let el = $(this);
      let valuefor = el.data('valuefor');
      if (valuefor){
	let el_type = el.prop('type');

	var value;
	if (el_type == 'checkbox'){
	  value = el.prop('checked');
	}else{
	  value = el.val();
	}
	let required = el.prop('required');
	let req_ok = required ? Boolean(value) : true;
	let origvalue = self._model_init_values[valuefor];
	if (value != origvalue && req_ok){
	  self._model_changed[valuefor] = value;
	}else if (value == origvalue){
	  delete self._model_changed[valuefor];
	}
      }
    });
  }

  _hasChanges(){
    return Object.keys(this._model_changed).length > 0;
  }

  _hasRequired(){
    throw "You must implement _hasRequired()";
  }

  _getSaveBtn(){
    return $('.save-btn-container button');
  }

  _checkHasChanges(){
    this._getChangesFromInput();
    let btn = this._getSaveBtn();
    let has_changed = this._hasChanges();
    let has_required = this._hasRequired();
    if (has_changed && has_required){
      btn.prop('disabled', false);
    }else{
      btn.prop('disabled', true);
    }
  }

  _clearNameAvailableInfo(){
    this._name_available = $(this._name_avail_s);
    this._name_available_indicator = $(this._name_avail_indicator_s);
    this._name_available_spinner = $(this._name_available_spinner);
    this._name_available.hide();
    this._name_available_indicator.hide();
    this._name_available_indicator.removeClass('fas fa-check').removeClass(
      'fas fa-times');

  }

  _handleNameAvailableInfo(is_available){

    if(is_available){
      this._name_available_indicator.addClass('fas fa-check');
      this._name_available.html('');
      this._checkHasChanges();
    }else{
      this._name_available_indicator.addClass('fas fa-times');
      this._name_available.html('Name not available');
    }

    this._name_available_spinner.hide();
    this._name_available.fadeIn(300);
    this._name_available_indicator.fadeIn(300);

  }

  async _checkNameAvailable(name){
    this._clearNameAvailableInfo();

    if (this._model_init_values['name'] == name || !name){
      this._checkHasChanges();
      this._name_available.html('');
      return false;
    }

    this._name_available_spinner.show();

    let r = await this.model.constructor.is_name_available(name);
    this._handleNameAvailableInfo(r);

    return r;
  }

  async _saveChanges(){

    this._save_btn_text.hide();
    this._save_btn_spinner.show();
    this._save_btn.prop('disabled', true);

    let cls_name = this.model.constructor.name;
    try{
      let changed = this._model_changed;
      await this.model.save(null, {attrs: changed});
      $.extend(this._model_init_values, changed);
      utils.showSuccessMessage(i18n(cls_name) + i18n(' updated'));
    }catch(e){
      console.error(e);
      this._save_btn.prop('disabled', false);
      utils.showErrorMessage(i18n('Error updating ') + i18n(cls_name));
    }
    this._save_btn_spinner.hide();
    this._save_btn_text.show();
  }

  _getRemoveModal(){
    throw new Error('You must implement _getRemoveModal()');
  }

  async _removeObj(){
    let modal = this._getRemoveModal();
    let cls_name = this.model.constructor.name;
    var error = false;
    try{
      await this.model.remove();
      utils.showSuccessMessage(i18n(cls_name) + i18n(' removed'));
    }catch(e){
      error = true;
      utils.showErrorMessage(i18n('Error deleting ') + i18n(cls_name.toLowerCase()));
    }
    modal.modal('hide');
    modal.on('hidden.bs.modal', function(e){
      if(!error){
	$(document).trigger('obj-removed-using-form');
      }
    });
  }

  _listen2save(template){
    let self = this;
    // save changes when clicking on save button
    let save_btn = $('#btn-save-obj');
    save_btn.on('click', function(e){
      self._saveChanges();
    });
  }

  _listen2remove(template){
    let self = this;
    let remove_btn = $('#btn-remove-obj');
    remove_btn.on('click', function(e){
      self._removeObj();
    });
  }

  _listen2name_available(template){
    let self = this;
    let check_name = _.debounce(function(name){
      self._checkNameAvailable(name);}, 500);
    $('.obj-details-name', template).on('input', function(e){
      let name = $(this).val();
      check_name(name);
    });
  }

  _listen2input_changes(template){
    let self = this;
    // check for changes to enable save button
    let check_changes = _.debounce(function(){self._checkHasChanges();}, 300);
    $('input', template).each(function(){
      let el = $(this);
      if(el.prop('type') == 'checkbox'){
	el.on('click', function(){
	  self._checkHasChanges();
	});
      }else{
	el.on('input', function(e){check_changes();});
      }
    });
  }

  _listen2events(template){
    this._listen2input_changes(template);
    this._listen2name_available(template);
    this._listen2save(template);
    this._listen2remove(template);
  }
}


class BaseListView extends Backbone.View{


  _get_view(model){
    throw new Error('You must implement _get_view()');
  }

  _render_obj(model, prepend=false){
    let view = this._get_view(model);
    let rendered = view.getRendered();
    if (prepend){
      this.$el.prepend(rendered.hide());
      rendered.slideDown('slow');
    }else{
      this.$el.append(rendered.hide().fadeIn(300));
    }
    return rendered;
  }

  _render_list(){
    $(this._container_selector).html(this.$el);
    var self = this;
    this.model.each(function(model){self._render_obj(model);});
    return true;
  }

  async _fetch_items(){
    throw new Error('You must define _fetch_items()');
  }

  async render_all(){
    wsconsumer.disconnect();
    await this._fetch_items();
    $('.wait-toxic-spinner').hide();
    $('.top-page-header-info-container').fadeIn();
    this._render_list();
  }

}


class BaseBuildDetailsView extends Backbone.View{

  constructor(options){
    super(options);
    this.build = options ? options.build : new Build();
    this._step_queue = new Array();
  }

  async _add2StepQueue(steps){
    let length = this._step_queue.length;
    let step = this._step_queue[length - 1];
    if (!steps){
      steps = this.build.get('steps');
    }
    let new_step = steps.models[steps.length -1];

    if (!step || new_step.get('index') > step.get('index')){
      this._step_queue.push(new_step);
    }else{
      this._step_queue.splice(0, 0, new_step);
    }
    await this._addStep();
  }

  _stepOk2Add(step){
    let index = step.get('index');
    if (this._last_step == null && index == 0){
      return true;
    }else if (this._last_step != null && this._last_step + 1 == index){
      return true;
    }
    return false;
  }

  async _addStep(){
    throw new Error('You must implement _addStep');
  }

}
