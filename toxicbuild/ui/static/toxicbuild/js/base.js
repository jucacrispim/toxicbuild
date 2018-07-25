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


class BaseModel extends Backbone.Model{

  sync(method, model, options){
    let url = _get_url(method, this, false);
    options.attrs = this.changed;
    options.url = url;
    let xsrf_token = Cookies.get('_xsrf');
    let headers = {'X-XSRFToken': xsrf_token};
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
}


class BaseCollection extends Backbone.Collection{

  parse(data){
    return data.items;
  }
}
