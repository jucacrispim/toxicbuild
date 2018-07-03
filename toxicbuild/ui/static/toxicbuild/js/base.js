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

class BaseModel{

  constructor(api_url){
    this.api_url = api_url;
  }

  async save(){
    let reqtype = this.id ? 'put' : 'post';
    let data = this._get_save_data();
    let resp = await jQuery.ajax({'url': this.api_url, 'type': reqtype,
				  'data': data});
    let obj = jQuery.parseJSON(resp);

    BaseModel._update_object(this, obj);

  }

  static async get(model_cls, kw){

    let query = BaseModel._format_query(kw);

    let url = this.api_url + query;
    let resp = await jQuery.ajax(url);
    let resp_obj = jQuery.parseJSON(resp);

    let obj = new model_cls();

    BaseModel._update_object(obj, resp_obj);
    return obj;
  }

  static async list(model_cls, kw){
    let query = BaseModel._format_query(kw);

    let url = this.api_url + query;
    let resp = await jQuery.ajax(url);
    let resp_list = jQuery.parseJSON(resp);
    let objs = new Array();
    for (let i in resp_list['items']){
      let obj = new model_cls();
      BaseModel._update_object(obj, resp_list['items'][i]);
      objs.push(obj);
    }
    return objs;
  }

  async delete(){
    if (!this.id){
      throw "Can't delete without an id";
    }

    await jQuery.ajax({'url': this.api_url + '?name=' + this.name,
		       'type': 'delete'});
  }

  _get_save_data(){
    let not_allowed = ['api_url'];
    let data = {};
    for (let attr in this){
      if (not_allowed.indexOf(attr) < 0){
	data[attr] = this[attr];
      }
    }
    return data;
  }

  static _format_query(kw){
    let query = '?';
    for (let key in kw){
      query += key + '=' + kw[key] + '&';
    }
    return query;
  }

  static _update_object(obj, new_obj){
    for (let attr in new_obj){
      obj[attr] = new_obj[attr];
    }

  }

}
