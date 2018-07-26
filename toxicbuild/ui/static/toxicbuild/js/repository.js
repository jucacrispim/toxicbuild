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

var TOXIC_REPO_API_URL = window.TOXIC_API_URL + 'repo/';

class Repository extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_REPO_API_URL;
  }

  async _post2api(url, body){
    let xsrf_token = Cookies.get('_xsrf');
    let headers = {'X-XSRFToken': xsrf_token};
    let resp = await jQuery.ajax(
      {'url': url, 'data': JSON.stringify(body), 'type': 'post',
       'contentType': "application/json", 'headers': headers});

    return resp;
  }

  async add_slave(slave){
    let url = this._api_url + 'add-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async remove_slave(slave){
    let url = this._api_url + 'remove-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async add_branch(branches_config){
    let url = this._api_url + 'add-branch?id=' + this.id;
    let body = {'add_branches': branches_config};
    let r = await this._post2api(url, body);
    let branches = this.get('branches');
    for (let i in branches_config){
      let branch = branches_config[i];
      branch['name'] = branch.branch_name;
      delete branch['branch_name'];
      branches.push(branch);
    }
    this.set('branches', branches);
    return r;
  }

  async remove_branch(branches){
    let url = this._api_url + 'remove-branch?id=' + this.id;
    let body = {'remove_branches': branches};
    let r = await this._post2api(url, body);
    let repo_branches = this.get('branches');
    let new_branches = [];
    for (let i in repo_branches){
      let branch = repo_branches[i];
      if (branches.indexOf(branch.name) < 0 && new_branches.indexOf(branch) < 0){
	new_branches.push(branch);
      }
    }
    this.set('branches', new_branches);
    return r;
  }

  async enable_plugin(plugin_config){
    let url = this._api_url + 'enable-plugin?id=' + this.id;
    return this._post2api(url, plugin_config);
  }

  async disable_plugin(plugin_name){
    let url = this._api_url + 'disable-plugin?id=' + this.id;
    let body = {'plugin_name': plugin_name};
    return this._post2api(url, body);
  }

  async start_build(branch, builder_name=null, named_tree=null,
		    slaves=null, builders_origin=null){
    let url = this._api_url + 'start-build?id=' + this.id;
    let body = {'branch': branch, 'builder_name': builder_name,
		'named_tree': named_tree, 'slaves': slaves,
		'builders_origin': builders_origin};
    return this._post2api(url, body);
  }

  async cancel_build(build_uuid){
    let url = this._api_url + 'cancel-build?id=' + this.id;
    let body = {'build_uuid': build_uuid};
    return this._post2api(url, body);
  }

  async enable(){
    let url = this._api_url + 'enable?id=' + this.id;
    return this._post2api(url);
  }

  async disable(){
    let url = this._api_url + 'disable?id=' + this.id;
    return this._post2api(url);
  }

  static async is_name_available(name){
    let model = new Repository();
    let r = await model.fetch({'name': name});
    try{
      r = model.parse(r);
    }catch(e){
      r = null;
    }
    return !Boolean(r);
  }

}


class RepositoryList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Repository;
    this.url = TOXIC_REPO_API_URL;
  }

}


class BaseRepositoryView extends Backbone.View{

  _get_kw(){
    let status = this.model.escape('status');
    let last_buildset = this.model.get('last_buildset') || {};
    let parallel_builds = this.model.escape('parallel_builds');
    let commit = last_buildset.commit ? last_buildset.commit.slice(0, 8) : '';
    commit = _.escape(commit);
    let branches = this.model.get('branches') || [];
    let escaped_branches = [];
    for (let i in branches){
      let branch = branches[i];
      let escaped_branch = {'name': _.escape(branch.name),
			    'notify_only_latest': branch.notify_only_latest};
      escaped_branches.push(escaped_branch);
    }

    let slaves = this.model.get('slaves') || [];
    let escaped_slaves = [];
    for (let i in slaves){
      let slave = slaves[i];
      let escaped_slave = {'name': _.escape(slave.name),
			   'host': _.escape(slave.host),
			   'port': _.escape(slave.port),
			   'use_ssl': slave.use_ssl,
			   'validate_cert': slave.validate_cert};
      escaped_slaves.push(escaped_slave);
    }
    let enabled = this.model.get('enabled');
    let full_name = this.model.escape('full_name');
    let details_link = '/' + full_name + '/settings';
    let url = this.model.escape('url');

    let kw = {'name': this.model.escape('name'),
	      'status': status,
	      'commit': commit,
	      'title': last_buildset.title,
	      'total_time': last_buildset.total_time,
	      'started': last_buildset.started,
	      'enabled': enabled,
	      'branches': escaped_branches,
	      'slaves': escaped_slaves,
	      'url': url,
	      'full_name': full_name,
	      'details_link': details_link,
	      'parallel_builds': parallel_builds,
	      'commit_date': last_buildset.commit_date};

    return kw;
  }

  _get_badge_class(status){
    let badge_classes = {'ready': 'secondary',
			 'running': 'primary',
			 'exception': 'exception',
			 'clone-exception': 'exception'};
    let badge_class = 'badge-' + badge_classes[status];
    return badge_class;
  }

  async _change_enabled(el){
    let toggle_group = jQuery('.toggle', el.parent().parent());
    let spinner = jQuery('.wait-change-enabled-spinner', el.parent().parent());
    toggle_group.hide();
    spinner.fadeIn(300);

    let enabled = el.is(':checked');
    if (enabled){
      await this.model.enable();
    }else{
      await this.model.disable();
    }

    spinner.hide();
    toggle_group.fadeIn(500);

    let container = jQuery(el.parent().parent());
    container.removeClass('repo-enabled').removeClass('repo-disabled');
    let indicator = jQuery('.toggle-handle', container);
    indicator.removeClass('fas fa-check repo-enabled-check').removeClass(
      'fas fa-times');
    if (enabled){
      indicator.addClass('fas fa-check repo-enabled-check');
    }else{
      indicator.addClass('fas fa-times repo-enabled-times');
    }
  }

  _listen2events(template){
    let checkbox = jQuery('.enabled-checkbox', template);
    let self = this;
    checkbox.change(function(){self._change_enabled(jQuery(this));});
  }

  _setEnabled(enabled, template){
    if (enabled){
      jQuery('.repository-info-enabled-container', template).addClass(
	'repo-enabled');
    }else{
      jQuery('.repository-info-enabled-container', template).addClass(
	'repo-disabled');
    }

  }
}

class RepositoryDetailsView extends BaseRepositoryView{

  constructor(full_name){
    super({'tagName': 'div'});
    this.model = new Repository();
    this.full_name = full_name;

    this.directive = {
      '#repo-details-name@value': 'name',
      '#repo-details-url@value': 'url',
      '#repo-parallel-builds@value': 'parallel_builds',
      '.repository-info-enabled-container input@checked': 'enabled',
      '.repo-branches-li': {
	'branch<-branches': {'.branch-name': 'branch.name',
			     '.remove-branch-btn@data-branch': 'branch.name'}},
      '.repo-slaves-li': {
	'slave<-slaves': {'.slave-name': 'slave.name'}}
    };

    this.template_selector = '#repo-details';
    this.compiled_template = null;
    this.container_selector = '#repo-details-container';
    this.container = null;
  }

  _getBranchModal(){
    let modal = jQuery('#addBranchModal');
    return modal;
  }
  async _checkNameAvailable(name){

    let selector = '#repo-name-available #available-text';
    let indicator_selector = '#repo-name-available .check-error-indicator';
    let spinner_selector = '.wait-name-available-spinner';
    let el = jQuery(selector);
    let indicator = jQuery(indicator_selector);
    let spinner = jQuery(spinner_selector);

    el.hide();
    indicator.hide();
    indicator.removeClass('fas fa-check').removeClass('fas fa-times');

    if (this.model._init_values['name'] == name){
      this._checkHasChanges();
      el.html('');
      return false;
    }

    spinner.show();

    let r = await Repository.is_name_available(name);

    if(r){
      indicator.addClass('fas fa-check');
      el.html('');
      this._checkHasChanges();
    }else{
      indicator.addClass('fas fa-times');
      el.html('Name not available');
    }

    spinner.hide();
    el.fadeIn(300);
    indicator.fadeIn(300);

    return r;
  }

  _getChangesFromInput(){
    let self = this;

    jQuery('input').each(function(){
      let el = jQuery(this);
      let valuefor = el.data('valuefor');
      if (valuefor){
	let value = el.val();

	let origvalue = self.model._init_values[valuefor];
	if (value != origvalue){
	  self.model.set(valuefor, value);
	  if (value == '' && valuefor == 'parallel_builds'){
	    self.model.changed[valuefor] = value || 0;
	  }

	}else{
	  delete self.model.changed[valuefor];
	}
      };
    });
  }

  _checkHasChanges(){
    this._getChangesFromInput();
    let btn = jQuery('.save-btn-container button');
    let has_changed = this.model.hasChanged();
    if (has_changed){
      btn.prop('disabled', false);
    }else{
      btn.prop('disabled', true);
    }
  }

  async _saveChanges(){
    let spinner = jQuery('.repo-details-buttons-container #save-repo-btn-spinner');
    let text = jQuery('.repo-details-buttons-container #save-repo-btn-text');

    text.hide();
    spinner.show();

    let btn = jQuery('.save-btn-container button');
    btn.prop('disabled', true);

    try{
      let changed = this.model.changed;
      await this.model.save();
      jQuery.extend(this.model._init_values, changed);
      utils.showSuccessMessage('Repository updated');
    }catch(e){
      btn.prop('disabled', false);
      utils.showErrorMessage('Error updating repository');
    }
    spinner.hide();
    text.show();
  }

  _hackHelpHeight(steps, type='increase'){
    let branches = this.model.get('branches') || [];
    if (branches.length <= 1 && type == 'increase'){
      return;
    }else if (branches.length < 1 && type == 'decrease'){
      return;
    }

    let step_modif = type == 'increase' ? 1 : -1;
    let step_size = 40 * step_modif;
    let container = jQuery('#branches-config-p');
    for (let i=0; i < steps; i++){
      let height = container.height();
      let new_height = step_size + height;
      container.height(new_height);
    }
  }

  _addBranchRow(branch){
    let directive = {'.branch-name': 'name',
		     '.remove-branch-btn@data-branch': 'name'};
    let template = $p('.repo-branches-li').compile(directive);
    let compiled = jQuery(template(branch));
    let container = jQuery('#repo-details #repo-branches-container');
    this._listen2remove_branch_event(compiled);
    container.append(compiled.hide().fadeIn(300));
    this._hackHelpHeight(1);
  }

  async _addBranch(){
    let text = jQuery("#add-branch-btn-text");
    let spinner = jQuery('#add-branch-btn-spinner');
    text.hide();
    spinner.show();
    let branch_name = jQuery('#repo-branch-name').val();
    let notify_only_latest = jQuery('#notify_only_latest').is(':checked');
    let branch = {'branch_name': branch_name,
		  'notify_only_latest': notify_only_latest};
    let confs =  [branch];
    try{
      await this.model.add_branch(confs);
      let branches = this.model.get('branches');
      this._handleBrachList(this.model.get('branches').length);
      this._addBranchRow({'name': branch_name,
			  'notify_only_latest': branch.notify_only_latest});
      let modal = this._getBranchModal();
      modal.modal('hide');
    }catch(e){
      utils.showErrorMessage('Error adding branch');
    }
    text.show();
    spinner.hide();
  }

  async _removeBrach(remove_el){
    let spinner = jQuery('.remove-branch-btn-spinner', remove_el.parent());
    remove_el.hide();
    spinner.show();
    let branch_name = remove_el.data('branch');
    let confs = [branch_name];
    try{
      await this.model.remove_branch(confs);
    }catch(e){
      remove_el.show();
      spinner.hide();
      utils.showErrorMessage('Error removing branch');
      return;
    }
    await remove_el.parent().hide();
    this._hackHelpHeight(1, 'decrease');
    this._handleBrachList(this.model.get('branches').length);
  }

  _initBranchFields(){
    jQuery('#repo-branch-name').val('');
    jQuery('#notify-only-latest').prop('checked', true);
    jQuery('#btn-add-branch').prop('disabled', true);
  }

  _enableAddBranchBtn(){
    let btn = jQuery('#btn-add-branch');
    let name_input = jQuery('#repo-branch-name');
    if (Boolean(name_input.val())){
      btn.prop('disabled', false);
    }else{
      btn.prop('disabled', true);
    }
  }

  _listen2remove_branch_event(template){
    let self = this;
    jQuery('.remove-branch-btn', template).on('click', function(e){
      let remove_el = jQuery(e.target);
      self._removeBrach(remove_el);
    });

  }

  _listen2events(template){
    let self = this;
    super._listen2events(template);

    // check repo name and enable save button
    let check_name = _.debounce(function(name){
      self._checkNameAvailable(name);}, 500);
    jQuery('#repo-details-name', template).on('input', function(e){
      let name = jQuery(this).val();
      check_name(name);
    });

    // check for changes to enable save button
    let check_changes = _.debounce(function(){self._checkHasChanges();}, 300);
    jQuery('input', template).each(function(){
      let el = jQuery(this);
      el.on('input', function(e){check_changes();});
    });

    // save changes when clicking on save button
    jQuery('#btn-save-repo', template).on('click', function(e){
      self._saveChanges();
    });

    jQuery('#addBranchModal').on('show.bs.modal', function(e){
      self._initBranchFields();
    });

    let enable_branch_btn = _.debounce(function(){self._enableAddBranchBtn();},
				       300);
    jQuery('#repo-branch-name').on('input', function(e){
      enable_branch_btn();
    });

    jQuery('#btn-add-branch').on('click', function(e){
      self._addBranch();
    });

    self._listen2remove_branch_event(template);
  }

  _handleBrachList(has_branches, template){
    var placeholder;
    if (template){
     placeholder = jQuery('#no-branch-placeholder', template);
    }else{
      placeholder = jQuery('#repo-details #no-branch-placeholder');
    }

    if (!has_branches){
      placeholder.fadeIn(300);
    }else{
      placeholder.hide();
    }
  }

  _setValidations(){
    jQuery('#repo-branch-name').validate({

      errorPlacement: function(error, element){
	element.addClass('form-control-error');
      },

      errorClass: "form-control-error",
      focusCleanup: true,
    });
  }

  async render_details(){
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    await this.model.fetch({'full_name': this.full_name});
    jQuery('.wait-toxic-spinner').hide();
    this.model._init_values = this.model.changed;
    // we need to set this to {} because when we fetch a model from the
    // remote host it is marked as changed since the initial model here
    // had no attributes.
    this.model.changed = {};

    let kw = this._get_kw();
    let has_branches = kw.branches.length ? true : false;
    let has_slaves = kw.slaves.length ? true : false;

    let compiled = jQuery(this.compiled_template(kw));
    let checkbox = jQuery('.enabled-checkbox', compiled);
    utils.checkboxToggle(checkbox);
    this._listen2events(compiled);

    this._setValidations();
    this._handleBrachList(has_branches, compiled);

    let enabled = kw['enabled'];
    this._setEnabled(enabled, compiled);
    this.container = jQuery(this.container_selector);
    this.container.html(compiled);
    this._hackHelpHeight(this.model.get('branches').length - 1, 'increase');
  }
}

class RepositoryInfoView extends BaseRepositoryView{
  // A view to display the repository information in the
  // repository list

  constructor(options, list_type){
    super(options);
    this.list_type = list_type;

    this.directives = {
      'short': {
	'.repository-info-name': 'name',
	'.repo-details-link@href': 'details_link',
	'.repository-info-status': 'status',
	'.buildset-commit': 'commit',
	'.buildset-title': 'title',
	'.buildset-total-time': 'total_time',
	'.buildset-started': 'started',
	'.buildset-commit-date': 'commit_date'},

      'enabled': {
	'.repository-info-name': 'name',
	'.repo-details-link@href': 'details_link',
	'.repository-info-enabled-container input@checked': 'enabled'}};

    this.directive = this.directives[this.list_type];
    this.template_selector = '.template .repository-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

  }

  render(){
    let kw = this._get_kw();
    let status = kw['status'];
    let badge_class = this._get_badge_class(status);

    let compiled = jQuery(this.compiled_template(kw));
    compiled.addClass('repo-status-' + status);
    jQuery('.badge', compiled).addClass(badge_class);

    let checkbox = jQuery('.enabled-checkbox', compiled);
    utils.checkboxToggle(checkbox);
    this._listen2events(compiled);

    let enabled = kw['enabled'];
    this._setEnabled(enabled, compiled);

    if (status == 'ready'){
      jQuery('.no-builds-info', compiled).show();
    }
    else{
      jQuery('.repository-info-last-buildset', compiled).show();
    }
    return compiled;
  }
}


class RepositoryListView extends Backbone.View{

  constructor(list_type){
    // list_type may be: 'enabled', 'short', 'full'
    let model = new RepositoryList();
    let options = {'tagName': 'ul',
		   'model': model};

    super(options);
    this.list_type = list_type;

  }

  initialize(){
    _.bindAll(this, 'render');
    var self = this;
    // this.model.bind('sync', function(){self._render_list_if_needed();});
  }

  _render_repo(model){
    let view = new RepositoryInfoView({'model': model},
				      this.list_type);
    let rendered = view.render();
    this.$el.append(rendered.hide().fadeIn(300));
    return rendered;
  }

  _render_list_if_needed(){
    // Renders the repository list if there are some repositories. If not
    // displays the welcome message
    jQuery('.wait-toxic-spinner').hide();
    if (this.model.length == 0){
      jQuery('#no-repos-info').fadeIn(300);
      return false;
    }

    jQuery('.top-page-repositories-info-container').show();
    jQuery('#repo-list-container').html(this.$el);
    var self = this;
    this.model.each(function(model){self._render_repo(model);});
    return true;
  }

  async render_enabled(){
    await this.model.fetch({'data': {'enabled': 'true'}});
    this._render_list_if_needed();
  }

  async render_all(){
    await this.model.fetch();
    this._render_list_if_needed();
  }
}
