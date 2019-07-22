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

var TOXIC_REPO_API_URL = window.TOXIC_API_URL + 'repo/';

class Repository extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_REPO_API_URL;
  }

  async add_slave(slave_id){
    let url = this._api_url + 'add-slave?' + 'id=' + this.id;
    let body = {'id': slave_id};
    return this._post2api(url, body);
  }

  async remove_slave(slave_id){
    let url = this._api_url + 'remove-slave?' + 'id=' + this.id;
    let body = {'id': slave_id};
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
		    builders_origin=null){
    let url = this._api_url + 'start-build?id=' + this.id;
    let body = {'branch': branch, 'builder_name': builder_name,
		'named_tree': named_tree};
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
    let r = await is_name_available(model, name);
    return r;
  }
}


class RepositoryList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    let self = this;
    this.model = Repository;
    this.url = TOXIC_REPO_API_URL;
    $(document).on('buildset_started buildset_finished', function(e, data){
      self.updateRepoStatus(data);
    });
  }

  updateRepoStatus(msg){
    let repo = this.get(msg['repository']['id']);
    let attrs = {'status': msg['status'],
		 'last_buildset': msg};
    repo.set(attrs);
  }

}


class BaseRepositoryView extends BaseFormView{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Repository();
    super(options);

    this.directive = {
      '.repo-details-name@value': 'name',
      '.repo-details-url@value': 'url',
      '.repo-parallel-builds@value': 'parallel_builds',
      '.repository-info-enabled-container input@checked': 'enabled',
      '.repo-branches-li': {
	'branch<-branches': {'.branch-name': 'branch.name',
			     '.remove-branch-btn@data-branch': 'branch.name'}},
      '.repo-slaves-li': {
	'slave<-slaves': {'.slave-name': 'slave.name',
			  'input@checked': 'slave.enabled',
			  'input@data-slave-id': 'slave.id'}}
    };

    this.template_selector = '#repo-details';
    this.compiled_template = null;
    this.container_selector = '#repo-details-container';
    this.container = null;
    this.slave_list = new SlaveList();
  }

  _get_kw(){
    let status = this.model.escape('status');
    let status_translation = i18n(status);
    let last_buildset = this.model.get('last_buildset') || {};
    let parallel_builds = parseInt(this.model.get('parallel_builds'));
    let commit = last_buildset.commit ? last_buildset.commit.slice(0, 8) : '';
    commit = _.escape(commit);
    let buildset_list_link = '/' + this.model.escape('full_name') + '/';
    let waterfall_link = '/' + this.model.escape('full_name') + '/' + 'waterfall';
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
	      'status': status_translation,
	      'original_status': status,
	      'commit': commit,
	      'title': _.escape(last_buildset.title),
	      'total_time': last_buildset.total_time,
	      'started': last_buildset.started,
	      'enabled': enabled,
	      'branches': escaped_branches,
	      'slaves': escaped_slaves,
	      'url': url,
	      'full_name': full_name,
	      'details_link': details_link,
	      'parallel_builds': parallel_builds,
	      'commit_date': last_buildset.commit_date,
	      'buildset_list_link': buildset_list_link,
	      'waterfall_link': waterfall_link};

    return kw;
  }

  _get_badge_class(status){
    return utils.get_badge_class(status);
  }

  async _change_enabled(el){
    let toggle_group = $('.toggle', el.parent().parent());
    let spinner = $('.wait-change-enabled-spinner', el.parent().parent());
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

    let container = $(el.parent().parent());
    container.removeClass('repo-enabled').removeClass('repo-disabled');
    let indicator = $('.toggle-handle', container);
    indicator.removeClass('fas fa-check repo-enabled-check').removeClass(
      'fas fa-times');
    if (enabled){
      indicator.addClass('fas fa-check repo-enabled-check');
    }else{
      indicator.addClass('fas fa-times repo-enabled-times');
    }
  }

  _listen2events(template){
    super._listen2events(template);
    let checkbox = $('.repo-enabled-checkbox', template);
    let self = this;
    checkbox.change(function(){self._change_enabled($(this));});
  }

  _setEnabled(enabled, template){
    if (enabled){
      $('.repository-info-enabled-container', template).addClass(
	'repo-enabled');
    }else{
      $('.repository-info-enabled-container', template).addClass(
	'repo-disabled');
    }
  }

  _getChangesFromInput(){
    super._getChangesFromInput();
    for (let key in this._model_changed){
      let value = this._model_changed[key];
      if (value == '' && key == 'parallel_builds'){
  	this._model_changed[key] = 0;
      }
    }
  }

  _hasRequired(){
    let has_name = $('.repo-details-name', this.container).val();
    let has_url = $('.repo-details-url', this.container).val();
    return Boolean(has_name) && Boolean(has_url);
  }

  async render_details(){
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
    $('.wait-toxic-spinner').hide();

    let kw = await this._get_kw();
    let has_branches = kw.branches.length ? true : false;

    let compiled = $(this.compiled_template(kw));
    let checkbox = $('.repo-enabled-checkbox', compiled);
    utils.checkboxToggle(checkbox);
    this.container = $(this.container_selector);
    this.container.html(compiled);
    this._listen2events(compiled);
  }
}

class RepositoryAddView extends BaseRepositoryView{

  constructor(){
    super(arguments);
    this.slaves = new SlaveList();
  }

  async render_details(){
    await this.slaves.fetch();
    this._model_init_values = this.model.changed;
    this.model.changed = {};
    $('#save-obj-btn-text').text('Add repository');
    await super.render_details();
    $('.repository-info-enabled-container').hide();
  }

  async _addRepo(){
    this.model.set('name', this._model_changed['name']);
    this.model.set('url', this._model_changed['url']);
    this.model.set('parallel_builds', 0);
    this.model.set('vcs_type', 'git');
    this.model.set('update_seconds', 10);
    let names = this.slaves.pluck('name');
    this.model.set('slaves', names);

    var r;
    try{
      r = await this.model.save();
      utils.showSuccessMessage(i18n('Repository added'));
    }catch(e){
      console.error(e);
      utils.showErrorMessage(i18n('Error adding repository'));
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
      self._addRepo();
    });
  }

}

class RepositoryDetailsView extends BaseRepositoryView{

  constructor(full_name){
    super();
    this.full_name = full_name;
  }

  _getBranchModal(){
    let modal = $('#addBranchModal');
    return modal;
  }

  _getRemoveModal(){
    let modal = $('#removeRepoModal');
    return modal;
  }

  _addBranchRow(branch){
    let directive = {'.branch-name': 'name',
		     '.remove-branch-btn@data-branch': 'name'};
    let template = $p('.repo-branches-li').compile(directive);
    let compiled = $(template(branch));
    let container = $('#repo-details #repo-branches-container');
    this._listen2remove_branch_event(compiled);
    container.append(compiled.hide().fadeIn(300));
  }

  async _addBranch(){
    let text = $("#add-branch-btn-text");
    let spinner = $('#add-branch-btn-spinner');
    text.hide();
    spinner.show();
    let branch_name = $('#repo-branch-name').val();
    let notify_only_latest = $('#notify_only_latest').is(':checked');
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
    let spinner = $('.remove-branch-btn-spinner', remove_el.parent());
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
    this._handleBrachList(this.model.get('branches').length);
  }

  _initBranchFields(){
    $('#repo-branch-name').val('');
    $('#notify-only-latest').prop('checked', true);
    $('#btn-add-branch').prop('disabled', true);
  }

  _enableAddBranchBtn(){
    let btn = $('#btn-add-branch');
    let name_input = $('#repo-branch-name');
    if (Boolean(name_input.val())){
      btn.prop('disabled', false);
    }else{
      btn.prop('disabled', true);
    }
  }

  _listen2remove_branch_event(template){
    let self = this;
    $('.remove-branch-btn', template).on('click', function(e){
      let remove_el = $(e.target);
      self._removeBrach(remove_el);
    });
  }

  _listen2events(template){
    let self = this;
    super._listen2events(template);

    $('#addBranchModal').on('show.bs.modal', function(e){
      self._initBranchFields();
    });

    let enable_branch_btn = _.debounce(function(){self._enableAddBranchBtn();},
				       300);
    $('#repo-branch-name').on('input', function(e){
      enable_branch_btn();
    });

    $('#btn-add-branch').on('click', function(e){
      self._addBranch();
    });

    self._listen2remove_branch_event(template);
  }

  _handleBrachList(has_branches, template){
    var placeholder;
    if (template){
     placeholder = $('#no-branch-placeholder', template);
    }else{
      placeholder = $('#repo-details #no-branch-placeholder');
    }

    if (!has_branches){
      placeholder.fadeIn(300);
    }else{
      placeholder.hide();
    }
  }

  _setSlaveEnabled(el){
    el.parent().removeClass('repo-enabled');
    el.parent().removeClass('repo-disabled');
    if (el.prop('checked')){
      el.parent().addClass('repo-enabled');
    }else{
      el.parent().addClass('repo-disabled');
    }
  }

  async _changeSlaveEnabled(el){
    this._setSlaveEnabled(el);

    let container = el.parent().parent();
    let toggle_group = $('.toggle', container);
    let spinner = $('.wait-change-enabled-spinner', container);
    toggle_group.hide();
    spinner.fadeIn(300);

    let m;
    let id = el.data('slave-id');
    if (el.prop('checked')){
      try{
	await this.model.add_slave(id);
      }catch(e){
	utils.showErrorMessage('Error adding slave');
      }
    }else{
      try{
	await this.model.remove_slave(id);
      }catch(e){
	utils.showErrorMessage('Error removing slave');
      }
    }
    spinner.hide();
    toggle_group.fadeIn(300);
  }

  _handleSlaveList(template){
    let self = this;

    let checkboxes = $('.slave-enabled-checkbox', template);
    checkboxes.each(function(){
      let el = $(this);
      utils.checkboxToggle(el);
      self._setSlaveEnabled(el);
      el.change(function(){self._changeSlaveEnabled($(this));});
    });
  }

  _setValidations(){
    $('#repo-branch-name').validate({

      errorPlacement: function(error, element){
	element.addClass('form-control-error');
      },

      errorClass: "form-control-error",
      focusCleanup: true,
    });
  }

  async _getSlavesKw(repo_slaves){
    let names = repo_slaves.map(s => s.name);
    let slaves_args = [];
    await this.slave_list.fetch();
    this.slave_list.each(function(slave){
      let name = slave.escape('name');
      let enabled = names.indexOf(name) < 0 ? false : true;
      let slave_kw = {'name': name, 'enabled': enabled,
		      'id': slave.get('id')};
      slaves_args.push(slave_kw);
    });

    return slaves_args;
  }

  async _get_kw(){
    let kw = super._get_kw();
    let slaves = await this._getSlavesKw(kw['slaves']);
    kw['slaves'] = slaves;
    return kw;
  }

  async render_details(){
    await this.model.fetch({'full_name': this.full_name});
    this._model_init_values = this.model.changed;
    // we need to set this to {} because when we fetch a model from the
    // remote host it is marked as changed since the initial model here
    // had no attributes.
    this.model.changed = {};

    await super.render_details();

    this._setValidations();
    let has_branches = this.model.get('branches').length ? true : false;
    this._handleBrachList(has_branches, this.container);

    this._handleSlaveList(this.container);
    let enabled = this.model.get('enabled');
    this._setEnabled(enabled, this.container);
    let branches = this.model.get('branches') || [];
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
	'.repository-info-name-container a@href': 'buildset_list_link',
	'.repository-info-status-container a@href': 'waterfall_link',
	'.repo-details-link@href': 'details_link',
	'.repository-info-status': 'status',
	'.buildset-commit': 'commit',
	'.buildset-title': 'title'},

      'enabled': {
	'.repository-info-name': 'name',
	'.repo-details-link@href': 'details_link',
	'.repository-info-name-container a@href': 'buildset_list_link',
	'.repository-info-enabled-container input@checked': 'enabled'}};

    this.directive = this.directives[this.list_type];
    this.template_selector = '.template .repository-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    let self = this;
    this.model.on({'change': function(){self.render();}});
  }

  render(){
    let kw = this._get_kw();
    let status = kw['original_status'];
    let badge_class = this._get_badge_class(status);
    let compiled = $(this.compiled_template(kw));
    compiled.addClass('repo-status-' + status.replace(' ', '-'));
    $('.badge', compiled).addClass(badge_class);

    let spinner_cog = $('.fa-cog', compiled);
    if (status != 'running'){
      spinner_cog.hide();
    }

    let checkbox = $('.repo-enabled-checkbox', compiled);
    utils.checkboxToggle(checkbox);
    this._listen2events(compiled);

    let enabled = kw['enabled'];
    this._setEnabled(enabled, compiled);

    if (status == 'ready'){
      $('.no-builds-info', compiled).show();
    }
    else{
      $('.repository-info-last-buildset', compiled).show();
    }
    this.$el.html(compiled);
    return this;
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

  _render_repo(model){
    let view = new RepositoryInfoView({'model': model},
				      this.list_type);
    let rendered = view.render().$el;
    this.$el.append(rendered.hide().fadeIn(300));
    return rendered;
  }

  _render_list_if_needed(){
    wsconsumer.connectTo('repo-status');
    // Renders the repository list if there are some repositories. If not
    // displays the welcome message
    $('.wait-toxic-spinner').hide();
    if (this.model.length == 0){
      $('.top-page-repositories-settings-info-container').fadeIn();
      $('#no-repos-info').fadeIn(300);
      return false;
    }
    $('.top-page-repositories-info-container').fadeIn();
    $('#repo-list-container').html(this.$el);
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
