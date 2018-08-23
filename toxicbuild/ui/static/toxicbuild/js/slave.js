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

var TOXIC_SLAVE_API_URL = window.TOXIC_API_URL + 'slave/';

class Slave extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_SLAVE_API_URL;
  }

  static async is_name_available(name){
    let model = new Slave();
    let r = await is_name_available(model, name);
    return r;
  }
}


class SlaveList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Slave;
    this.url = TOXIC_SLAVE_API_URL;
  }
}

class BaseSlaveView extends BaseFormView{

  _get_kw(){
    let name = this.model.escape('name');
    let host = this.model.escape('host');
    let full_name = this.model.escape('full_name');
    let port = this.model.escape('port');
    let details_link = '/slave/' + full_name;
    let token = this.model.escape('token');
    let use_ssl = this.model.get('use_ssl');
    let verify_cert = this.model.get('verify_cert');
    return {name: name, host: host, port: port, details_link: details_link,
	    token: token, use_ssl: use_ssl, verify_cert: verify_cert,
	    use_ssl_el_id: 'slave-use-ssl', full_name: full_name,
	    'verify_cert_el_id': 'slave-verify-cert'};
  }

}

class SlaveInfoView extends BaseSlaveView{
  // The info about a slave shown in a slave list

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Slave();
    super(options);

    this.directive = {
      '.slave-info-name': 'name',
      '.slave-details-link@href': 'details_link',
      '.slave-info-host': 'host',
      '.slave-info-port': 'port',
    };

    this.template_selector = '.template .slave-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

  }

  getRendered(){
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    return compiled;
  }

}

class SlaveListView extends Backbone.View{

  constructor(){
    let model = new SlaveList();
    let options = {'tagName': 'ul',
		   'model': model};

    super(options);
    this._info_view = SlaveInfoView;
 }

  _render_slave(model){
    let view = new this._info_view({'model': model});
    let rendered = view.getRendered();
    this.$el.append(rendered.hide().fadeIn(300));
    return rendered;
  }

  _render_list(){
    $('#slave-list-container').html(this.$el);
    var self = this;
    this.model.each(function(model){self._render_slave(model);});
    return true;
  }

  async render_all(){
    await this.model.fetch();
    $('.wait-toxic-spinner').hide();
    $('.top-page-slaves-info-container').fadeIn();
    this._render_list();
  }

}

class SlaveDetailsView extends BaseSlaveView{

  constructor(options){
    options = options || {'tagName': 'div'};
    super(options);
    this.name = options.name;
    this.model = this.model || new Slave();
    this.model._init_values = {};
    this.model._changed = {};

    this.directive = {
      '.slave-details-name@value': 'name',
      '.slave-details-host@value': 'host',
      '.slave-details-port@value': 'port',
      '.slave-details-token@value': 'token',
      '.slave-details-use-ssl@checked': 'use_ssl',
      '.slave-details-use-ssl@id': 'use_ssl_el_id',
      '.slave-details-verify-cert@checked': 'verify_cert',
      '.slave-details-verify-cert@id': 'verify_cert_el_id'};

    this.template_selector = '#slave-details';
    this.compiled_template = null;
    this.container_selector = '#slave-details-container';
    this.container = null;
    this.slave_list = new SlaveList();
  }

  _hasRequired(){
    let has_name = $('.slave-details-name', this.container).val();
    let has_host = $('.slave-details-host', this.container).val();
    let has_port = $('.slave-details-port', this.container).val();
    let has_token = $('.slave-details-token', this.container).val();
    return (Boolean(has_name) && Boolean(has_host) && Boolean(has_port) &&
	    Boolean(has_token));
  }

  async render_details(){
    await this.model.fetch({name: this.name});

    this._model_init_values = this.model.changed;
        this.compiled_template = $p(this.template_selector).compile(
      this.directive);
    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();

    let compiled = $(this.compiled_template(kw));
    this._listen2events(compiled);
    this.container = $(this.container_selector);
    this.container.html(compiled);
  }
}
