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

describe('RepositoryTest', function(){
  beforeEach(function(){
    spyOn(jQuery, 'ajax');
    let window_spy = jasmine.createSpy();
    window_spy.TOXIC_API_URL = 'http://localhost:1234/';
    window = window_spy;
    this.model = new Repository();
  });

  it('test-post2api', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let url = 'http://bla.nada/';
    let body = {'some': 'data'};
    let repo = new Repository();
    await repo._post2api(url, body);
    let called = jQuery.ajax.calls.allArgs()[0][0];
    let called_keys = [];
    for(let key in called){
      called_keys.push(key);
    }

    let expected = ['url', 'data', 'type', 'contentType', 'headers'];
    expect(called_keys).toEqual(expected);
  });

  it('test-add-slave', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let slave = new Slave();
    let repo = new Repository();
    let expected_url = repo._api_url + 'add-slave?id=' + repo.id;
    await repo.add_slave(slave);
    let called_url = jQuery.ajax.calls.allArgs()[0][0]['url'];
    expect(called_url).toEqual(expected_url);
  });

  it('test-remove-slave', async function(){
    let slave = new Slave();
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_url = repo._api_url + 'remove-slave?id=' + repo.id;
    let expected_body = {'id': slave.id};
    await repo.remove_slave(slave);
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

  it('test-is-name-available', async function(){
    spyOn(this.model, 'fetch').and.returnValue({});
    let r = await Repository.is_name_available('some-name');
    expect(r).toBe(true);
  });

  it('test-is-name-exception', async function(){
    spyOn(this.model, 'fetch').and.returnValue({'items': []});
    let r = await Repository.is_name_available('some-name');
    expect(r).toBe(true);
  });

});

describe('BaseRepositoryViewTest', function(){

  beforeEach(function(){
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
    let el = jQuery('<input type="checkbox" checked>');
    await this.view._change_enabled(el);
    expect(this.view.model.enable).toHaveBeenCalled();
  });

  it('test-change-enabled-repo-disabled', async function(){
    this.view.model = new Repository({'name': 'bla'});
    this.view.model.disable = jasmine.createSpy('disable');
    let el = jQuery('<input type="checkbox">');
    await this.view._change_enabled(el);
    expect(this.view.model.disable).toHaveBeenCalled();
  });

  it('test-listen2evets', function(){
    spyOn(jQuery.fn, 'change');
    let el = jasmine.createSpy('el');
    el.change = jasmine.createSpy('change');
    this.view._listen2events(el);
    expect(jQuery.fn.change).toHaveBeenCalled();
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
    repo_details += '+#repo-details-url+input#repo-parallel-builds';
    repo_details += '+#repo-name-available .check-error-indicator';
    repo_details += '+.repository-info-enabled-container input';
    repo_details += '+.repo-branches-li';
    repo_details += '+.repo-slaves-li';
    this.template = affix('#repo-details ' + repo_details);
    jQuery('.repo-branches-li', this.template).affix(
      'span.branch-name+.remove-branch-btn');
    jQuery('.repo-slaves-li', this.template).affix('.slave-name');
    this.view = new RepositoryDetailsView('full-name');
    this.view.model._init_values = {};
  });

  it('test-render-details', async function(){
    spyOn(this.view.model, 'fetch');
    await this.view.render_details();
    let el_index = this.view.container.html().indexOf('repo-details-name');
    expect(el_index > 0).toBe(true);
  });

  it('test-checkNameAvailable-available', async function(){
    spyOn(Repository, 'is_name_available').and.returnValue(true);
    spyOn(this.view, '_checkHasChanges');
    this.view.model._init_values['name'] = 'asdf';
    await this.view._checkNameAvailable('name');
    let el_index = this.template.html().indexOf('fa-check');
    expect(el_index > 0).toBe(true);
  });

  it('test-checkNameAvailable-not-available', async function(){
    spyOn(Repository, 'is_name_available').and.returnValue(false);
    spyOn(this.view, '_checkHasChanges');
    this.view.model._init_values['name'] = 'asdf';
    await this.view._checkNameAvailable('name');
    let el_index = this.template.html().indexOf('fa-times');
    expect(el_index > 0).toBe(true);
  });

  it('test-getChangesFromInput-different-value', function(){
    let fist_in = affix('input');
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('asfd');
    this.view.model._init_values = {'name': 'some'};
    spyOn(this.view.model, 'set');
    this.view._getChangesFromInput();
    let call_count = this.view.model.set.calls.allArgs().length;
    expect(call_count).toEqual(1);
  });

  it('test-getChangesFromInput-same-as-init-value', function(){
    let fist_in = affix('input');
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('asfd');
    this.view.model._init_values = {'name': 'asfd'};
    spyOn(this.view.model, 'set');
    this.view._getChangesFromInput();
    let call_count = this.view.model.set.calls.allArgs().length;
    expect(call_count).toEqual(0);
  });

  it('test-getChangesFromInput-return-to-init-value', function(){
    let fist_in = affix('input');
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('qwer');
    this.view.model._init_values = {'name': 'asfd'};
    spyOn(this.view.model, 'set');
    this.view._getChangesFromInput();
    second_in.val('asfd');
    this.view._getChangesFromInput();
    expect(this.view.model.changed.hasOwnProperty('name')).toBe(false);
  });

  it('test-checkHasChanges-changed', function(){
    spyOn(this.view, '_getChangesFromInput');
    spyOn(this.view.model, 'hasChanged').and.returnValue(true);
    affix('.save-btn-container button');
    this.view._checkHasChanges();
    let btn = jQuery('.save-btn-container button');
    expect(btn.prop('disabled')).toBe(false);
  });

  it('test-checkHasChanges-not-changed', function(){
    spyOn(this.view, '_getChangesFromInput');
    spyOn(this.view.model, 'hasChanged').and.returnValue(false);
    affix('.save-btn-container button');
    this.view._checkHasChanges();
    let btn = jQuery('.save-btn-container button');
    expect(btn.prop('disabled')).toBe(true);
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
    let remove_el = jQuery('.remove-el');
    remove_el.data('branch', 'bla');
    this.view.model.set('branches', []);
    spyOn(this.view.model, 'remove_branch');
    await this.view._removeBrach(remove_el);
    expect(this.view.model.remove_branch).toHaveBeenCalled();

  });

  it('test-removeBranch-exception', async function(){
    affix('div.outer span.remove-el');
    let remove_el = jQuery('.remove-el');
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
    let placeholder = jQuery('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches, template);
    expect(placeholder.is(':visible')).toBe(true);
  });

  it('test-handleBranchList-has-branches-template', function(){
    let template = affix('div #no-branch-placeholder');
    let has_branches = true;
    let placeholder = jQuery('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches, template);
    expect(placeholder.is(':visible')).toBe(false);
  });

  it('test-handleBranchList-no-branches-no-template', function(){
    affix('#repo-details #no-branch-placeholder');
    let has_branches = false;
    let placeholder = jQuery('#no-branch-placeholder');
    placeholder.hide();
    this.view._handleBrachList(has_branches);
    expect(placeholder.is(':visible')).toBe(true);
  });

  it('test-handleBranchList-has-branches-no-template', function(){
    affix('#repo-details #no-branch-placeholder');
    let has_branches = true;
    let placeholder = jQuery('#no-branch-placeholder');
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

  it('test-hackHelpHeight-increase-not-first', function(){
    let config = affix('#branches-config-p');
    config.height(10);
    this.view.model.set('branches', [{}, {}]);
    this.view._hackHelpHeight(2);
    config = jQuery('#branches-config-p');
    expect(config.height()).toEqual(90);
  });

  it('test-hackHelpHeight-increase-first', function(){
    let config = affix('#branches-config-p');
    config.height(10);
    this.view.model.set('branches', [{}]);
    this.view._hackHelpHeight(2);
    config = jQuery('#branches-config-p');
    expect(config.height()).toEqual(10);
  });

  it('test-hackHelpHeight-decrease-not-last', function(){
    let config = affix('#branches-config-p');
    config.height(100);
    this.view.model.set('branches', [{}]);
    this.view._hackHelpHeight(2, 'decrease');
    config = jQuery('#branches-config-p');
    expect(config.height()).toEqual(20);
  });

  it('test-hackHelpHeight-decrease-last', function(){
    let config = affix('#branches-config-p');
    config.height(100);
    this.view.model.set('branches', []);
    this.view._hackHelpHeight(2, 'decrease');
    config = jQuery('#branches-config-p');
    expect(config.height()).toEqual(100);
  });

});

describe('RepositoryListViewTest', function(){

  beforeEach(function(){
    let infos = '.repository-info-name+.repository-info-status';
    infos += '+.buildset-commit+.buildset-title+.buildset-total-time';
    infos += '+.buildset-stated+.buildset-commit-date+.buildset-started';
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
