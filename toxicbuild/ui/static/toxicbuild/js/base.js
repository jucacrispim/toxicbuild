// Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

  sync(method, model, options){
    let url = _get_url(method, this, false);
    options.attrs = _.extend(this._changes, options.attrs);
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
    return data.items;
  }

  sync(method, model, options){
    options.headers = _getHeaders();
    let r = super.sync(method, model, options);
    return r;
  }
}


class BaseView extends Backbone.View{

  constructor(options){
    options = options || {};
    super(options);
    this.model = options.model || null;
    this._model_init_values = {};
    this._model_changed = {};

  }

  _getChangesFromInput(){
    let self = this;

    $('input').each(function(){
      let el = $(this);
      let valuefor = el.data('valuefor');
      if (valuefor){
	let value = el.val();
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
}
