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

var TOXIC_NOTIFICATION_API_URL = window.TOXIC_API_URL + 'notification/';


class Notification extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_NOTIFICATION_API_URL;
  }

  _get_url(repo_id){
    let url = this._api_url + this.get('name') + '/' + repo_id;
    return url;
  }

  async enable(repo_id, conf){
    let url = this._get_url(repo_id);
    let r = await this._request2api('post', url, conf);
    return r;
  }

  async disable(repo_id){
    let url = this._get_url(repo_id);
    let r = await this._request2api('delete', url, {});
    return r;
  }

  async update(repo_id, conf){
    let url = this._get_url(repo_id);
    let r = await this._request2api('put', url, conf);
    return r;
  }

  getIcon(){
    return window.STATIC_URL + 'toxicbuild/img/'+ this.get('name') + '.png';
  }
}


class NotificationList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Notification;
    this.url = TOXIC_NOTIFICATION_API_URL;
  }
}


class NotificationConfigView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Notification();
    super(options);
  }

  _getFields(){
    let fields = {};
    let non_fields = ['name', 'pretty_name', 'events',
		      'changed', 'cid', 'collection',
		      'statuses', 'branches'];
    for (let i in this.model.attributes){
      let attribute = this.model.attributes[i];
      if (non_fields.indexOf(attribute.name) >= 0 || !attribute.pretty_name ||
	  attribute.name.indexOf('_') == 0){
	continue;
      }
      fields[attribute.pretty_name] = {name: _.escape(attribute.name),
				       required: attribute.required || false,
				       value: _.escape(attribute.value),
				       type: attribute.type};
    }
    return fields;
  }

  _checkChanges(){
    var ok = true;
    $('#notificationModal input').each(function(){
      let el = $(this);
      let required = el.prop('required');
      let value = el.val();
      if (required && !value){
	ok = false;
      }
    });

    let btn = $('#btn-enable-notification');
    if(ok){
      btn.prop('disabled', false);
    }else{
      btn.prop('disabled', true);
    }
  }

  _parseValue(value, type){
    if (type == 'list'){
      value = value.split(',');
      value = value.map(function(v){return v.trim();}, value);
    }
    return value;
  }

  _getSaveData(){
    let save_data = {};
    let fields = this._getFields();
    for (let k in fields){
      let field = fields[k];
      let name = field.name;
      let input = $('#id-' + name);
      let value = input.val();
      value = this._parseValue(value, field.type);
      save_data[name] = value;
    }
    return save_data;
  }

  _mergeSaveData(data, enabled){
    this.model.set('enabled', enabled);
    for (let i in this.model.attributes){
      let attribute = this.model.attributes[i];
      let value = data[attribute.name];
      try{
	attribute.value = value;
      }catch(e){
	// pass
      }
    }
  }

  async saveNotification(){
    let data = this._getSaveData();
    let repo_id = $('#repo-id').val();
    let enabled = this.model.get('enabled');
    let modal = $('#notificationModal');
    let name = this.model.get('name');
    let check = $('#' + name + '-is-enabled');
    try{
      if (enabled){
	await this.model.update(repo_id, data);
	utils.showSuccessMessage(this.model.get('pretty_name') + ': ' +
				 i18n('notification updated'));
	modal.modal('hide');
      }else{
	await this.model.enable(repo_id, data);
	modal.modal('hide');
	utils.showSuccessMessage(this.model.get('pretty_name') + ": " +
				 i18n('notification enabled'));
      }
      check.show();
      this._mergeSaveData(data, true);
    }catch(e){
      modal.modal('hide');
      utils.showErrorMessage(i18n('Error on notifications'));
    }
  }

  async disableNotification(){
    let repo_id = $('#repo-id').val();
    let modal = $('#notificationModal');
    let name = this.model.get('name');
    try{
      await this.model.disable(repo_id);
      modal.modal('hide');
      utils.showSuccessMessage(this.model.get('pretty_name') + ': ' +
			       i18n('notification disabled'));
      this._mergeSaveData({}, false);
      $('#' + name + '-is-enabled').hide();
    }catch(e){
      modal.modal('hide');
      utils.showErrorMessage(i18n('Error disabling notification'));
    }

  }

  getRendered(){
    let outer = $(document.createElement('div'));
    let fields = this._getFields();
    for (let k in fields){
      let value = fields[k].value || '';
      let label = $(document.createElement('label'));
      label.text(i18n(k));

      let required = fields[k].required;
      let input = $(document.createElement('input'));
      input.val(value);
      input.prop('required', required);
      input.addClass('form-control');
      input.prop('type', 'text');
      input.prop('id', 'id-' + fields[k].name);
      outer.append(label);
      outer.append(input);
    }
    return outer;
  }

  _toggleAdvanced(){
    let container = $('#notification-config-advanced');
    let angle_container = $('#advanced-angle-span');

    container.toggle(300);
    if (angle_container.hasClass('fa-angle-down')){
      angle_container.removeClass('fa-angle-down').addClass('fa-angle-right');
    }else{
      angle_container.removeClass('fa-angle-right').addClass('fa-angle-down');
    }
  }

  _listen2save(template){
    let self = this;
    let btn = $('#btn-enable-notification');
    btn.unbind('click');
    btn.on('click', async function(){
      await self.saveNotification();
    });
  }

  _listen2disable(template){
    let self = this;
    let btn = $('#btn-remove-obj');
    btn.unbind('click');
    btn.on('click', async function(){
      await self.disableNotification();
    });
  }

  _listen2changes(template){
    let self = this;
    let check = _.debounce(function(){self._checkChanges();}, 300);
    $('#notificationModal').unbind('input');
    $('#notificationModal').on('input', function(e){
      check();
    });
  }

  _listen2events(template){
    let self = this;
    let el = $('.notification-config-advanced-span');
    el.unbind('click');
    el.on('click', function(e){
      self._toggleAdvanced();
    });

    this._listen2changes(template);
    this._listen2save(template);

    this._listen2disable(template);
  }

  _handleButtons(template){
    let enabled = this.model.get('enabled');
    let disable_btn = $('.disable-notif-btn-container');

    if (enabled){
      disable_btn.show();
      $('#enable-notification-btn-text').html('Update');
    }else{
      disable_btn.hide();
      $('#enable-notification-btn-text').html('Enable');
    }
  }

  render(){
    let rendered = this.getRendered();
    this._listen2events(rendered);
    this._handleButtons(rendered);
    $('#notification-modal-icon').prop('src', this.model.getIcon());
    $('.modal-title').text(this.model.get('pretty_name'));
    $('#notification-modal-body').append(rendered);
  }
}


class NotificationInfoView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Notification();
    super(options);

    this.directive = {
      '.notification-pretty-name': 'pretty_name',
      '.notification-img @src': 'img',
      '.notification-cid @data-cid': 'cid',
      '.fa-check @id': '#{name}-is-enabled',
    };

    this.template_selector = '.template .notification-item';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

  }

  _get_kw(){
    let name = this.model.get('name');
    let pretty_name = this.model.get('pretty_name');
    let img = this.model.getIcon();
    let cid = this.model.cid;
    let enabled = this.model.get('enabled');
    return {pretty_name: pretty_name, img: img,
	    cid: cid, enabled: enabled,
	    name: name};
  }

  getRendered(){
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    let check = $('.fa-check', compiled);
    if (kw.enabled){
      check.show();
    }else{
      check.hide();
    }
    return compiled;
  }

}


class NotificationListView extends BaseListView{

  constructor(repo_id){
    let model = new NotificationList();
    let options = {'tagName': 'ul',
		   'model': model};

    super(options);
    this.repo_id = repo_id;
    this._container_selector = '#repo-notifications-container';
  }

  async _fetch_items(){
    await this.model.fetch({data: {'repo_id': this.repo_id}});
  }

  _get_view(model){
    return new NotificationInfoView({model: model});
  }

  _listen2events(){
    let self = this;
    $('#notificationModal').on('show.bs.modal', function(e){
      let el = $(e.relatedTarget);
      let cid = el.data('cid');
      let notif = self.model._byId[cid];
      let config_view = new NotificationConfigView({model: notif});
      config_view.render();
    });

    $('#notificationModal').on('hidden.bs.modal', function(e){
      $('#notification-modal-body').html('');
      let btn = $('#btn-enable-notification');
      btn.prop('disabled', true);
    });
  }

  render_all(){
    super.render_all(arguments);
    this._listen2events();
  }

}
