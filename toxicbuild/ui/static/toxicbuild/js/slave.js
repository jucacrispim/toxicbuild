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
    let on_demand = this.model.get('on_demand');
    let instance_confs = this.model.get('instance_confs');
    let instance_id = instance_confs ? _.escape(
      instance_confs['instance_id']) : null;
    let region = instance_confs ? _.escape(instance_confs['region']) : null;

    return {name: name, host: host, port: port, details_link: details_link,
	    token: token, use_ssl: use_ssl, verify_cert: verify_cert,
	    use_ssl_el_id: 'slave-use-ssl', full_name: full_name,
	    'verify_cert_el_id': 'slave-verify-cert',
	    on_demand_el_id: 'slave-on-demand', instance_id: instance_id,
	    region: region, on_demand: on_demand};
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

class SlaveListView extends BaseListView{

  constructor(){
    let model = new SlaveList();
    let options = {'tagName': 'ul',
		   'model': model};

    super(options);
    this._container_selector = '#slave-list-container';
  }

  async _fetch_items(){
    await this.model.fetch();
  }

  _get_view(model){
    return new SlaveInfoView({model: model});
  }

}

class BaseSlaveDetailsView extends BaseSlaveView{

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
      '.slave-details-on-demand@id': 'on_demand_el_id',
      '.slave-details-on-demand@checked': 'on_demand',
      '.slave-details-instance-id@value': 'instance_id',
      '.slave-details-region@value': 'region',
      '.slave-details-verify-cert@checked': 'verify_cert',
      '.slave-details-verify-cert@id': 'verify_cert_el_id'};

    this.template_selector = '#slave-details';
    this.compiled_template = null;
    this.container_selector = '#slave-details-container';
    this.container = null;
  }

  _hasRequired(){
    let has_name = $('.slave-details-name', this.container).val();
    let has_host = $('.slave-details-host', this.container).val();
    let has_port = $('.slave-details-port', this.container).val();
    let has_token = $('.slave-details-token', this.container).val();
    let on_demand = $('.slave-details-on-demand', this.container).is(
      ':checked');
    let instance_id = $('.slave-details-instance-id', this.container).val();
    let region = $('.slave-details-region', this.container).val();
    let inst_confs = on_demand ? Boolean(instance_id) && Boolean(region) : true;
    let host_ok = on_demand ? true : Boolean(has_host);

    return (inst_confs && Boolean(has_name) && host_ok &&
	    Boolean(has_port) && Boolean(has_token));
  }

  _handleInstanceConfs(on_demand, template){
    let el = template ? $('.instance-confs-container', template) :
	$('.instance-confs-container');
    let text_el = $('.instance-confs-text');

    if (!on_demand){
      if (template){
	el.hide();
	text_el.hide();
      }else{
	el.slideUp();
	text_el.slideUp();
      }

    }else{
      el.slideDown();
      text_el.slideDown();
      el.attr('style', 'display:flex;');
    }
    this._checkHasChanges();
  }

  _handleOnDemandChange(el){
    let on_demand = el.is(':checked');
    this._handleInstanceConfs(on_demand);
  }

  render_details(){

    this._model_init_values = this.model.changed;
        this.compiled_template = $p(this.template_selector).compile(
      this.directive);
    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();

    let compiled = $(this.compiled_template(kw));
    this._listen2events(compiled);
    this.container = $(this.container_selector);
    let el = $('#slave-on-demand', compiled);
    let on_demand = el.is(':checked');
    let self = this;
    el.change(function(){
      self._handleOnDemandChange($(this));
    });
    this._handleInstanceConfs(on_demand, compiled);
    this.container.html(compiled);
  }
}

class SlaveDetailsView extends BaseSlaveDetailsView{

  async render_details(){
    await this.model.fetch({name: this.name});
    super.render_details();
  }

  _getRemoveModal(){
    let modal = $('#removeSlaveModal');
    return modal;
  }

}


class SlaveAddView extends BaseSlaveDetailsView{

  render_details(){
    super.render_details();
    $('.delete-btn-container').hide();
    $('#save-obj-btn-text').text('Add slave');
  }

  async _addSlave(){
    this.model.set('name', this._model_changed['name']);
    this.model.set('host', this._model_changed['host']);
    this.model.set('port', this._model_changed['port']);
    this.model.set('token', this._model_changed['token']);
    this.model.set('use_ssl', this._model_changed['use_ssl']);
    this.model.set('validate_cert', this._model_changed['validate_cert']);
    let on_demand = this._model_changed['on_demand'];
    this.model.set('on_demand', on_demand);
    let instance_confs = {instance_id: this._model_changed['instance_id'],
			  region: this._model_changed['region']};
    this.model.set('instance_confs', instance_confs);
    let instance_type = on_demand ? 'ec2' : null;
    this.model.set('instance_type', instance_type);

    var r;
    try{
      r = await this.model.save();
      utils.showSuccessMessage(i18n('Slave added'));
    }catch(e){
      console.error(e);
      utils.showErrorMessage(i18n('Error adding slave'));
      return;
    }
    $(document).trigger('obj-added-using-form', r['full_name']);
  }

  _listen2events(template){
    let self = this;
    super._listen2events(template);

    let btn = $('#btn-save-obj');
    btn.unbind('click');
    btn.on('click', function(e){
      self._addSlave();
    });
  }
}
