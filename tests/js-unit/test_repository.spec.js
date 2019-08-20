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

describe('RepositoryTest', function(){
  beforeEach(function(){
    spyOn($, 'ajax');
    let window_spy = jasmine.createSpy();
    window_spy.TOXIC_API_URL = 'http://localhost:1234/';
    window = window_spy;
    this.model = new Repository();
  });

  it('test-add-slave', async function(){
    $.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let slave = new Slave();
    let repo = new Repository();
    let expected_url = repo._api_url + 'add-slave?id=' + repo.id;
    await repo.add_slave(slave);
    let called_url = $.ajax.calls.allArgs()[0][0]['url'];
    expect(called_url).toEqual(expected_url);
  });

  it('test-remove-slave', async function(){
    let slave = new Slave();
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_url = repo._api_url + 'remove-slave?id=' + repo.id;
    let expected_body = {'id': slave.id};
    await repo.remove_slave(slave.id);
    let called_url = repo._post2api.calls.allArgs()[0][0];
    let called_body = repo._post2api.calls.allArgs()[0][1];
    expect(called_url).toEqual(expected_url);
    expect(called_body).toEqual(expected_body);
  });

  it('test-add-branch', async function(){
    let branches_config = [
      {'name': 'some-branch', 'notify_only_latest': true}];
    let repo = new Repository({'branches': []});
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_body = {'add_branches': branches_config};
    let expected_url = repo._api_url + 'add-branch?id=' + repo.id;

    await repo.add_branch(branches_config);

    let called_url = repo._post2api.calls.allArgs()[0][0];
    let called_body = repo._post2api.calls.allArgs()[0][1];
    expect(called_url).toEqual(expected_url);
    expect(called_body).toEqual(expected_body);
    expect(repo.get('branches').length).toEqual(1);
  });

  it('test-remove-branch', async function(){
    let branches = ['master', 'other'];
    let repo = new Repository({'branches': [{'name': 'master'},
					    {'name': 'other'},
					    {'name': 'third'}]});
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_body = {'remove_branches': branches};
    let expected_url = repo._api_url + 'remove-branch?id=' + repo.id;

    await repo.remove_branch(branches);

    let called_url = repo._post2api.calls.allArgs()[0][0];
    let called_body = repo._post2api.calls.allArgs()[0][1];
    expect(called_url).toEqual(expected_url);
    expect(called_body).toEqual(expected_body);
    expect(repo.get('branches').length).toEqual(1);
  });

  it('test-enable-plugin', async function(){
    let plugin_config = {'plugin_name': 'my-plugin',
			 'branches': ['master', 'bug-*'],
			 'statuses': ['fail', 'success']};
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.enable_plugin(plugin_config);
    let expected_url = repo._api_url + 'enable-plugin?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-disable-plugin', async function(){
    let plugin = {'pluign_name': 'my-pluign'};
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.disable_plugin(plugin);
    let expected_url = repo._api_url + 'disable-plugin?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-start-build', async function(){
    let branch = 'master';
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.start_build(branch);
    let expected_url = repo._api_url + 'start-build?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-cancel-build', async function(){
    let build_uuid = 'some-uuid';
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.cancel_build(build_uuid);
    let expected_url = repo._api_url + 'cancel-build?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-enable', async function(){
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.enable();
    let expected_url = repo._api_url + 'enable?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-disable', async function(){
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.disable();
    let expected_url = repo._api_url + 'disable?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-add_envvars', async function(){
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.add_envvars({env: 'var'});
    let expected_url = repo._api_url + 'add-envvars?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-rm_envvars', async function(){
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.rm_envvars({env: 'var'});
    let expected_url = repo._api_url + 'rm-envvars?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-replace_envvars', async function(){
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.replace_envvars({env: 'var'});
    let expected_url = repo._api_url + 'replace-envvars?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-is-name-available', async function(){
    let r = await Repository.is_name_available('some-name');
    expect(r).toBe(true);
  });
});

describe('RepositoryListTest', function(){

  beforeEach(function(){
    this.list = new RepositoryList();
  });

  it('test-updateRepoStatus', function(){
    let model = new Repository();
    model.set('status', 'somestatus');
    model.set('id', 'myid');
    this.list.set(model);

    let msg = {'repository': {'id': 'myid'}, 'status': 'otherstatus'};
    this.list.updateRepoStatus(msg);
    expect(model.get('status')).toEqual('otherstatus');
  });

});

describe('BaseRepositoryViewTest', function(){

  beforeEach(function(){
    affix('.template #repo-details-container #repo-details-name');
    let repo_details = 'input.repo-details-name+input.repo-details-url';
    repo_details += '+#repo-details-url+input.repo-parallel-builds';
    repo_details += '+#repo-name-available .check-error-indicator';
    repo_details += '+.repository-info-enabled-container input';
    repo_details += '+.repo-branches-li';
    repo_details += '+.repo-slaves-li';
    this.template = affix('#repo-details ' + repo_details);
    $('.repo-branches-li', this.template).affix(
      'span.branch-name+.remove-branch-btn');
    $('.repo-slaves-li', this.template).affix('.slave-name+input');

    this.view = new BaseRepositoryView();
  });

  it('test-get-kw-with-last-buildset', function(){
    let buildset = {'commit': 'asdf'};
    this.view.model = new Repository({'name': 'bla',
				      'last_buildset': buildset});
    let kw = this.view._get_kw();
    let commit = 'asdf';
    expect(kw['commit']).toEqual(commit);
  });

  it('test-get-kw-without-last-buildset', function(){
    let buildset = {'commit': 'asdf'};
    this.view.model = new Repository({'name': 'bla',
				      'last_buildset': {}});
    let kw = this.view._get_kw();
    let commit = '';
    expect(kw['commit']).toEqual(commit);
  });

  it('test-get-kw-with-branches', function(){
    let branches = [{'name': 'master', 'notify_only_latest': true}];
    this.view.model = new Repository({'name': 'bla',
				      'branches': branches});
    let kw = this.view._get_kw();
    expect(kw['branches'][0]['name']).toEqual('master');
  });

  it('test-get-kw-with-slaves', function(){
    let slaves = [{'name': 'some-slave', 'token': '123', 'host': 'localhost',
		   'port': 1234, 'use_ssl': false, 'validade_cert': false}];
    this.view.model = new Repository({'name': 'bla',
				      'slaves': slaves});
    let kw = this.view._get_kw();
    expect(kw['slaves'][0]['name']).toEqual('some-slave');
  });

  it('test-get-badge-class', function(){
    let badge_class = this.view._get_badge_class('running');
    expect(badge_class).toEqual('badge-primary');
  });


  it('test-change-enabled-repo-enable', async function(){
    this.view.model = new Repository({'name': 'bla'});
    this.view.model.enable = jasmine.createSpy('enable');
    let el = $('<input type="checkbox" checked>');
    await this.view._change_enabled(el);
    expect(this.view.model.enable).toHaveBeenCalled();
  });

  it('test-change-enabled-repo-disabled', async function(){
    this.view.model = new Repository({'name': 'bla'});
    this.view.model.disable = jasmine.createSpy('disable');
    let el = $('<input type="checkbox">');
    await this.view._change_enabled(el);
    expect(this.view.model.disable).toHaveBeenCalled();
  });

  it('test-listen2evets', function(){
    spyOn($.fn, 'change');
    let el = jasmine.createSpy('el');
    el.change = jasmine.createSpy('change');
    this.view._listen2events(el);
    expect($.fn.change).toHaveBeenCalled();
  });

  it('test-set-enabled-enable', function(){
    let enabled = true;
    let template = affix('div .repository-info-enabled-container');
    this.view._setEnabled(enabled, template);
    let el_index = template.html().indexOf('repo-enabled');
    expect(el_index > 0).toBe(true);
  });

  it('test-set-enabled-disable', function(){
    let enabled = false;
    let template = affix('div .repository-info-enabled-container');
    this.view._setEnabled(enabled, template);
    let el_index = template.html().indexOf('repo-disabled');
    expect(el_index > 0).toBe(true);
  });

  it('test-getChangesFromInput', function(){
    this.view._model_changed['parallel_builds'] = '';
    this.view._getChangesFromInput();
    expect(this.view._model_changed['parallel_builds']).toEqual(0);
  });

  it('test-hasRequired-no-name', function(){
    $('.repo-details-name', this.view.container).val('');
    $('.repo-details-url', this.view.container).val('/bla/ble');
    let r = this.view._hasRequired();
    expect(r).toBe(false);
  });

  it('test-hasRequired-no-url', function(){
    $('.repo-details-name', this.view.container).val('somename');
    $('.repo-details-url', this.view.container).val('');
    let r = this.view._hasRequired();
    expect(r).toBe(false);
  });

  it('test-hasRequired-ok', function(){
    $('.repo-details-name', this.view.container).val('somename');
    $('.repo-details-url', this.view.container).val('/bla/ble');
    let r = this.view._hasRequired();
    expect(r).toBe(true);
  });

  it('test-render-details', async function(){
    this.view.model.set('branches', []);
    await this.view.render_details();
    let el_index = this.view.container.html().indexOf('repo-details-name');
    expect(el_index > 0).toBe(true);
  });

});

describe('RepositoryInfoViewTest', function(){

  beforeEach(function(){
    let infos = '.repository-info-name+.repository-info-status';
    infos += '+.buildset-commit+.buildset-title+.buildset-total-time';
    infos += '+.buildset-stated+.buildset-commit-date+.buildset-started';
    affix('.template .repository-info ' + infos);
    this.view = new RepositoryInfoView();
  });

  it('test-render', function(){
    let buildset = {'commit': 'asdf'};
    this.view.model = new Repository({'name': 'bla',
				      'last_buildset': buildset});
    spyOn(this.view, 'compiled_template');
    this.view.render();
    expect(this.view.compiled_template).toHaveBeenCalled();
  });

});


describe('RepositoryDetailsViewTest', function(){

  beforeEach(function(){
    this.model = new Repository({'name': 'bla',
				 'last_buildset': {}});
    this.model.fetch = jasmine.createSpy('fetch');
    affix('.template #repo-details-container #repo-details-name');
    let repo_details = 'input#repo-details-name+input#repo-details-url';
    repo_details += '+#repo-details-url+input.repo-parallel-builds';
    repo_details += '+#repo-name-available .check-error-indicator';
    repo_details += '+.repository-info-enabled-container input';
    repo_details += '+.repo-branches-li';
    repo_details += '+.repo-slaves-li';
    this.template = affix('#repo-details ' + repo_details);
    $('.repo-branches-li', this.template).affix(
      'span.branch-name+.remove-branch-btn');
    $('.repo-slaves-li', this.template).affix('.slave-name+input');
    this.view = new RepositoryDetailsView('full-name');
    this.view.model._init_values = {};
  });

  it('test-addBranch-ok', async function(){
    affix('#repo-branch-name');
    affix('#notify_only_latest');
    spyOn(this.view.model, 'add_branch');
    await this.view._addBranch();
    expect(this.view.model.add_branch).toHaveBeenCalled();
  });

  it('test-addBranch-exception', async function(){
    affix('#repo-branch-name');
    affix('#notify_only_latest');
    spyOn(this.view.model, 'add_branch').and.throwError('error');
    spyOn(utils, 'showErrorMessage');
    await this.view._addBranch();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-removeBranch-ok', async function(){
    affix('div.outer span.remove-el');
    let remove_el = $('.remove-el');
    remove_el.data('branch', 'bla');
    this.view.model.set('branches', []);
    spyOn(this.view.model, 'remove_branch');
    await this.view._removeBrach(remove_el);
    expect(this.view.model.remove_branch).toHaveBeenCalled();

  });

  it('test-removeBranch-exception', async function(){
    affix('div.outer span.remove-el');
    let remove_el = $('.remove-el');
    remove_el.data('branch', 'bla');

    spyOn(this.view.model, 'remove_branch').and.throwError('bad remove');
    spyOn(utils, 'showErrorMessage');
    await this.view._removeBrach(remove_el);
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-addBranchRow', function(){
    let container = affix('#repo-details #repo-branches-container');
    let branch = {'name': 'bla'};
    this.view._addBranchRow(branch);
    expect(container.html().indexOf('bla') > 0).toBe(true);
  });

  it('test-initBranchFields', function(){
    let name_input = affix('#repo-branch-name');
    let notify_input = affix('#notify-only-latest');
    name_input.val('asdf');
    notify_input.prop('checked', false);
    this.view._initBranchFields();
    expect(notify_input.prop('checked')).toBe(true);
    expect(name_input.val()).toEqual('');
  });

  it('test-enableBranchBtn-no-value', function(){
    let name_input = affix('#repo-branch-name');
    let btn = affix('#btn-add-branch');
    name_input.val('');
    this.view._enableAddBranchBtn();
    expect(btn.prop('disabled')).toBe(true);
  });

  it('test-enableBranchBtn-value', function(){
    let name_input = affix('#repo-branch-name');
    let btn = affix('#btn-add-branch');
    name_input.val('asdf');
    this.view._enableAddBranchBtn();
    expect(btn.prop('disabled')).toBe(false);
  });

  it('test-handleBranchList-no-branches-template', function(){
    let template = affix('div #no-branch-placeholder');
    let has_branches = false;
    let placeholder = $('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches, template);
    expect(placeholder.is(':visible')).toBe(true);
  });

  it('test-handleBranchList-has-branches-template', function(){
    let template = affix('div #no-branch-placeholder');
    let has_branches = true;
    let placeholder = $('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches, template);
    expect(placeholder.is(':visible')).toBe(false);
  });

  it('test-handleBranchList-no-branches-no-template', function(){
    affix('#repo-details #no-branch-placeholder');
    let has_branches = false;
    let placeholder = $('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches);
    expect(placeholder.is(':visible')).toBe(true);
  });

  it('test-handleBranchList-has-branches-no-template', function(){
    affix('#repo-details #no-branch-placeholder');
    let has_branches = true;
    let placeholder = $('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches);
    expect(placeholder.is(':visible')).toBe(false);
  });

  it('test-saveChanges-ok', async function(){
    spyOn(this.view.model, 'save');
    spyOn(utils, 'showSuccessMessage');
    await this.view._saveChanges();
    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });

  it('test-saveChanges-exception', async function(){
    spyOn(this.view.model, 'save').and.throwError('bad save');
    spyOn(utils, 'showErrorMessage');
    await this.view._saveChanges();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-getSlavesKw', async function(){
    let repo_slaves = [{'name': 'bla'}];
    spyOn(this.view.slave_list, 'fetch');

    this.view.slave_list.each = function(cb){
      let slaves = [new Slave({'name': 'bla', 'id': '1'}),
		    new Slave({'name': 'ble', 'id': '2'})];
      for (let i in slaves){
	let slave = slaves[i];
	cb(slave);
      }
    };

    let slaves = await this.view._getSlavesKw(repo_slaves);
    let expected = [{'name': 'bla', 'enabled': true, 'id': '1'},
		    {'name': 'ble', 'enabled': false, 'id': '2'}];
    expect(expected).toEqual(slaves);

  });

  it('test-setSlaveEnabled-enabled', function(){
    affix('div .slave-enabled-checkbox');
    let el = $('.slave-enabled-checkbox');
    el.prop('checked', true);
    this.view._setSlaveEnabled(el);
    el = $('.slave-enabled-checkbox');
    expect(el.parent().hasClass('repo-enabled')).toBe(true);
  });

  it('test-setSlaveEnabled-disabled', function(){
    affix('div .slave-enabled-checkbox');
    let el = $('.slave-enabled-checkbox');
    el.prop('checked', false);
    this.view._setSlaveEnabled(el);
    el = $('.slave-enabled-checkbox');
    expect(el.parent().hasClass('repo-disabled')).toBe(true);
  });

  it('test-changeSlaveEnabled-enabled-ok', async function(){
    spyOn(utils, 'showErrorMessage');
    spyOn(this.view.model, 'add_slave');
    let el = affix('input');
    el.prop('checked', true);
    await this.view._changeSlaveEnabled(el);
    expect(this.view.model.add_slave).toHaveBeenCalled();
    expect(utils.showErrorMessage).not.toHaveBeenCalled();
  });

  it('test-changeSlaveEnabled-enabled-exception', async function(){
    spyOn(utils, 'showErrorMessage');
    spyOn(this.view.model, 'add_slave').and.throwError();
    let el = affix('input');
    el.prop('checked', true);
    await this.view._changeSlaveEnabled(el);
    expect(this.view.model.add_slave).toHaveBeenCalled();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-changeSlaveEnabled-disabled-ok', async function(){
    spyOn(utils, 'showErrorMessage');
    spyOn(this.view.model, 'remove_slave');
    let el = affix('input');
    el.prop('checked', false);
    await this.view._changeSlaveEnabled(el);
    expect(this.view.model.remove_slave).toHaveBeenCalled();
    expect(utils.showErrorMessage).not.toHaveBeenCalled();
  });

  it('test-changeSlaveEnabled-disabled-exeption', async function(){
    spyOn(utils, 'showErrorMessage');
    spyOn(this.view.model, 'remove_slave').and.throwError();
    let el = affix('input');
    el.prop('checked', false);
    await this.view._changeSlaveEnabled(el);
    expect(this.view.model.remove_slave).toHaveBeenCalled();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

});

describe('RepositoryListViewTest', function(){

  beforeEach(function(){
    let infos = '.repository-info-name+.repository-info-status';
    infos += '+.buildset-commit+.buildset-title+.buildset-total-time';
    infos += '+.buildset-stated+.buildset-commit-date+.buildset-started';
    infos += '+.repository-info-name-container a';
    infos += '+.repository-info-status-container a';
    infos += '+.repo-details-link';
    affix('.template .repository-info ' + infos);
    affix('#repo-list-container');
  });

  it('test-render-repo', function(){
    let buildset = {'commit': 'asdf'};
    let model = new Repository({'id': 'some-id', 'name': 'somename',
				'last_buildset': buildset});
    let view = new RepositoryListView('short');
    let rendered = view._render_repo(model);
    expect(rendered.html().indexOf('somename') >= 0).toBe(true);
  });

  it('test-render-enabled', function(){
    let view = new RepositoryListView();
    spyOn(view.model, 'fetch');
    view.render_enabled();
    let called_args = view.model.fetch.calls.allArgs()[0][0];
    let expected = {'data': {'enabled': 'true'}};
    expect(expected).toEqual(called_args);
  });

  it('test-render-all', function(){
    let view = new RepositoryListView();
    spyOn(view.model, 'fetch');
    view.render_all();
    let called_args = view.model.fetch.calls.allArgs()[0][0];
    expect(called_args).toBe(undefined);
  });

});

describe('RepositoryAddViewTest', function(){

  beforeEach(function(){
    this.view = new RepositoryAddView();
    affix('#repo-details');
  });

  it('test-addRepo-ok', async function(){
    spyOn($.fn, 'trigger');
    spyOn(this.view.model, 'save').and.returnValue({'full_name': 'bla'});
    await this.view._addRepo();
    expect($.fn.trigger).toHaveBeenCalled();
  });

  it('test-addRepo-exception', async function(){
    spyOn($.fn, 'trigger');
    spyOn(this.view.model, 'save').and.throwError();
    await this.view._addRepo();
    expect($.fn.trigger).not.toHaveBeenCalled();
  });

  it('test-render-details', async function(){
    spyOn(this.view.slaves, 'fetch');
    this.view.directive = {};
    let enabled_container = $('.repository-info-enabled-container');
    enabled_container.show();
    await this.view.render_details();
    enabled_container = $('.repository-info-enabled-container');
    expect(enabled_container.is(':visible')).toBe(false);
  });
});


describe('EnvvarRowView-test', function(){

  beforeEach(function(){
    affix('.template .envvars-row');
    let tmpl = $('.template .envvars-row');
    tmpl.affix('input.envvars-key');
    tmpl.affix('input.envvars-value');
    this.view = new EnvvarRowView('VAR', 'the-value');
  });

  it('test-render', function(){
    spyOn($.fn, 'show');
    this.view.render();
    expect(this.view.$el.html().indexOf('VAR') > -1).toBe(true);
    expect($.fn.show).toHaveBeenCalled();
  });

  it('test-render-no-key', function(){
    let view = new EnvvarRowView('', '');
    spyOn($.fn, 'show');
    view.render();
    expect($.fn.show).not.toHaveBeenCalled();
  });

  it('test-isKey-true', function(){
    let el = $(document.createElement('input'));
    el.addClass('envvars-key');
    let r = this.view._isKey(el);

    expect(r).toBe(true);
  });

  it('test-isKey-false', function(){
    let el = $(document.createElement('input'));
    el.addClass('envvars-val');
    let r = this.view._isKey(el);

    expect(r).toBe(false);
  });

  it('test-handleInput-ok', function(){
    affix('.envvars-row .col input.envvars-key', this.view.$el);
    let row = $('.envvars-row', this.view.$el);
    row.affix('input.envvars-val');
    let key = $('.envvars-key');
    key.val('asdf');
    let val = $('.envvars-value');
    val.val('asdf');

    this.view.showTimes = jasmine.createSpy();

    this.view._handleInput(key);
    expect(this.view.showTimes).toHaveBeenCalled();
  });

  it('test-handleInput', function(){
    affix('.envvars-row .col input.envvars-key', this.view.$el);
    let row = $('.envvars-row', this.view.$el);
    row.affix('input.envvars-val');
    let val = $('.envvars-val');
    val.val('asdf');
    this.view.showTimes = jasmine.createSpy();

    this.view._handleInput(val);
    expect(this.view.showTimes).not.toHaveBeenCalled();
  });

  it('test-hideEnvvars', function(){
    affix('.envvars-row .envvar-remove .fa-times', this.view.$el);
    let el = $('.fa-times', this.view.$el);
    spyOn($.fn, 'fadeOut');
    this.view._hideEnvvars(el);

    expect($.fn.fadeOut).toHaveBeenCalled();
  });


});


describe('RepositoryEnvvarsView-test', function(){

  beforeEach(function(){
    affix('.envvar-rows-container');
    affix('.template .envvars-row .col');
    let tmpl = $('.template .envvars-row .col');
    tmpl.affix('input.envvars-key');
    tmpl.affix('input.envvars-value');
    let repo = jasmine.createSpy();
    this.view = new RepositoryEnvvarsView({'ONE-VAR': 'one-val',
					   'OTHER-VAR': 'other-val'},
					  repo);
  });

  it('test-render', function(){
    this.view.render();
    expect(this.view.$el.html().indexOf('ONE-VAR') > -1).toBe(true);
    expect(this.view.$el.html().indexOf('OTHER-VAR') > -1).toBe(true);
  });

  it('test-addRow', function(){
    spyOn(EnvvarRowView.prototype, 'render');
    spyOn($.fn, 'append');
    this.view.addRow();
    expect(EnvvarRowView.prototype.render).toHaveBeenCalled();
    expect($.fn.append).toHaveBeenCalled();
  });

  it('test-cleanView', function(){
    spyOn($.fn, 'off');
    this.view.cleanView();
    expect($.fn.off).toHaveBeenCalled();
  });

  it('test-getEnvvars', function(){
    this.view.render();
    let envvars = this.view._getEnvvars();
    let expected = {'ONE-VAR': 'one-val',
		    'OTHER-VAR': 'other-val'};
    expect(envvars).toEqual(expected);
  });

  it('test-getEnvvars-dont-set-rows', function(){
    this.view.render();
    this.view.rows = [];
    let envvars = this.view._getEnvvars(false);
    let expected = {'ONE-VAR': 'one-val',
		    'OTHER-VAR': 'other-val'};
    expect(envvars).toEqual(expected);
    expect(this.view.rows).toEqual([]);
  });

  it('test-saveEnvvars-ok', async function(){
    this.view.repo.replace_envvars = jasmine.createSpy();
    spyOn(utils, 'showSuccessMessage');

    await this.view.saveEnvvars();

    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });

  it('test-saveEnvvars-error', async function(){
    this.view.repo.replace_envvars = jasmine.createSpy().and.throwError();
    spyOn(utils, 'showErrorMessage');

    await this.view.saveEnvvars();

    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

});
