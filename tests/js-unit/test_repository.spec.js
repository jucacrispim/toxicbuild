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
  });

  it('test-get', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'name': 'somerepo'}));
    let repo = await Repository.get({'id': 'some-id'});
    expect(repo.name).toEqual('somerepo');
  });

  it('test-list', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify(
      {'items': [{'name': 'somerepo'}, {'name': 'otherrepo'}]}));
    let repos = await Repository.list();
    expect(repos.length).toEqual(2);
  });

  it('test-post2api', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let url = 'http://bla.nada/';
    let body = {'some': 'data'};
    let repo = new Repository();
    await repo._post2api(url, body);
    let called = jQuery.ajax.calls.allArgs()[0][0];
    let expected = {'url': url, 'data': body, 'type': 'post'};
    expect(called).toEqual(expected);
  });

  it('test-add-slave', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let slave = new Slave();
    let repo = new Repository();
    let expected_url = repo.api_url + 'add-slave?id=' + repo.id;
    await repo.add_slave(slave);
    let called_url = jQuery.ajax.calls.allArgs()[0][0]['url'];
    expect(called_url).toEqual(expected_url);
  });

  it('test-remove-slave', async function(){
    let slave = new Slave();
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_url = repo.api_url + 'remove-slave?id=' + repo.id;
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
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_body = {'add_branches': branches_config};
    let expected_url = repo.api_url + 'add-branch?id=' + repo.id;
    await repo.add_branch(branches_config);
    let called_url = repo._post2api.calls.allArgs()[0][0];
    let called_body = repo._post2api.calls.allArgs()[0][1];
    expect(called_url).toEqual(expected_url);
    expect(called_body).toEqual(expected_body);
  });

  it('test-remove-branch', async function(){
    let branches = ['master', 'other'];
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    let expected_body = {'remove_branches': branches};
    let expected_url = repo.api_url + 'remove-branch?id=' + repo.id;
    await repo.remove_branch(branches);
    let called_url = repo._post2api.calls.allArgs()[0][0];
    let called_body = repo._post2api.calls.allArgs()[0][1];
    expect(called_url).toEqual(expected_url);
    expect(called_body).toEqual(expected_body);
  });

  it('test-enable-plugin', async function(){
    let plugin_config = {'plugin_name': 'my-plugin',
			 'branches': ['master', 'bug-*'],
			 'statuses': ['fail', 'success']};
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.enable_plugin(plugin_config);
    let expected_url = repo.api_url + 'enable-plugin?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-disable-plugin', async function(){
    let plugin = {'pluign_name': 'my-pluign'};
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.disable_plugin(plugin);
    let expected_url = repo.api_url + 'disable-plugin?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-start-build', async function(){
    let branch = 'master';
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.start_build(branch);
    let expected_url = repo.api_url + 'start-build?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

  it('test-cancel-build', async function(){
    let build_uuid = 'some-uuid';
    let repo = new Repository();
    repo._post2api = jasmine.createSpy('_post2api');
    await repo.cancel_build(build_uuid);
    let expected_url = repo.api_url + 'cancel-build?id=' + repo.id;
    let called_url = repo._post2api.calls.allArgs()[0][0];
    expect(called_url).toEqual(expected_url);
  });

});
