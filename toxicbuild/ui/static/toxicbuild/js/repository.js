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

class Repository extends BaseModel{

  constructor(){
    let api_url = window.TOXIC_API_URL + '/repo/';
    super(api_url);
  }

  static async get(kw){
    let r = await super.get(Repository, kw);
    return r;
  }

  static async list(kw){
    let r = await super.list(Repository, kw);
    return r;
  }

  async _post2api(url, body){
    let resp = await jQuery.ajax({'url': url, 'data': body, 'type': 'post'});
    return jQuery.parseJSON(resp);
  }

  async add_slave(slave){
    let url = this.api_url + 'add-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async remove_slave(slave){
    let url = this.api_url + 'remove-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async add_branch(branches_config){
    let url = this.api_url + 'add-branch?id=' + this.id;
    let body = {'add_branches': branches_config};
    return this._post2api(url, body);
  }

  async remove_branch(branches){
    let url = this.api_url + 'remove-branch?id=' + this.id;
    let body = {'remove_branches': branches};
    return this._post2api(url, body);
  }

  async enable_plugin(plugin_config){
    let url = this.api_url + 'enable-plugin?id=' + this.id;
    return this._post2api(url, plugin_config);
  }

  async disable_plugin(plugin_name){
    let url = this.api_url + 'disable-plugin?id=' + this.id;
    let body = {'plugin_name': plugin_name};
    return this._post2api(url, body);
  }

  async start_build(branch, builder_name=null, named_tree=null,
		    slaves=null, builders_origin=null){
    let url = this.api_url + 'start-build?id=' + this.id;
    let body = {'branch': branch, 'builder_name': builder_name,
		'named_tree': named_tree, 'slaves': slaves,
		'builders_origin': builders_origin};
    return this._post2api(url, body);

  }

  async cancel_build(build_uuid){
    let url = this.api_url + 'cancel-build?id=' + this.id;
    let body = {'build_uuid': build_uuid};
    return this._post2api(url, body);
  }

}
