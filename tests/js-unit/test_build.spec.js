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

describe('BuildTest', function(){

  it('test_getSteps', function(){
    let build_info = {'uuid': 'some-uuid',
		      'steps': [{'command': 'ls'}]};
    let build = new Build(build_info);
    expect(build.get('steps')[0] instanceof BuildStep).toBe(true);
  });
});


describe('BuildSetTest', function(){

  beforeEach(function(){
    let buildset_info = {'builds': [{'uuid': 'some-uuid',
				     'steps': [{'command': 'bla'}]}]};
    this.buildset = new BuildSet(buildset_info);

  });

  it('test-getBuilds', function(){
    this.buildset.attributes.builds = this.buildset._getBuilds(
      this.buildset.get('builds'));
    expect(this.buildset.get('builds')[0] instanceof Build).toBe(true);
  });

  it('test-getBuild', function(){
    this.buildset.attributes.builds = this.buildset._getBuilds(
      this.buildset.get('builds'));
    expect(this.buildset._getBuild('some-uuid').get('uuid')).toEqual(
      'some-uuid');
  });

  it('test-getBuild-error', function(){
    let self = this;
    this.buildset.attributes.builds = this.buildset._getBuilds(
      this.buildset.get('builds'));
    expect(function(){self.buildset._getBuild('bad-uuid');}).toThrow();
  });

  it('test-updateBuild', function(){
    let data = {'status': 'success', 'uuid': 'some-uuid'};
    this.buildset.attributes.builds = this.buildset._getBuilds(
      this.buildset.get('builds'));
    this.buildset._updateBuild(data);
    let build = this.buildset._getBuild('some-uuid');
    expect(build.get('status')).toEqual('success');
  });

});

describe('BuildSetLisTest', function(){
  beforeEach(function(){
    this.list = new BuildSetList();
  });

  it('test-updateBuildSet', function(){
    this.list.add({'id': 'some-id'});
    let data = {'id': 'some-id', 'title' :'some title'};
    this.list.updateBuildSet(data);
    let model = this.list.get('some-id');
    expect(model.get('title')).toEqual('some title');
  });

});

describe('BuildDetailsViewTest', function(){

  beforeEach(function(){
    affix('.template #build-details');
    let container = $('#build-details');
    container.affix('.build-command');
    container.affix('.build-number');
    container.affix('.commit-author');
    container.affix('.build-status');
    container.affix('.build-output');
    container.affix('.build-started');
    container.affix('.builder-name');
    container.affix('.commit-title');
    container.affix('.commit-branch');
    container.affix('.repo-name');
    container.affix('.build-total-time');
    this.view = new BuildDetailsView({build_uuid: 'some-uuid'});
  });

  it('test-render', async function(){
    spyOn(this.view.model, 'fetch');
    this.view.model.set({repository: {name: 'bla'}});
    this.view.model.set({builder: {name: 'ble'}});
    await this.view.render();
    expect($('.wait-toxic-spinner').is('visible')).toBe(false);
    expect(this.view.model.fetch).toHaveBeenCalled();
  });
});

describe('BuildsetInfoViewTest', function(){

  beforeEach(function(){
    affix('.template .buildset-info');
    let container = $('.buildset-info');
    container.affix('.buildset-title');
    container.affix('.buildset-branch');
    container.affix('.buildset-status');
    container.affix('.buildset-commit');
    container.affix('.buildset-commit-date');
    container.affix('.buildset-started');
    container.affix('.buildset-total-time');
    container.affix('.buildset-title-container a');
    this.view = new BuildSetInfoView();
  });

  it('test-getRendered-not-started', function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail',
						 started: null});
    spyOn($.fn, 'show');
    this.view.getRendered();
    expect($.fn.show).not.toHaveBeenCalled();
  });

  it('test-getRendered-started', function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail',
						 started: 'some str datetime'});

    spyOn($.fn, 'show');
    this.view.getRendered();
    expect($.fn.show).toHaveBeenCalled();
  });

  it('test-getRendered-not-running', function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail'});

    spyOn($.fn, 'show');
    let r = this.view.getRendered();
    expect($('.fa-cog', r).is('visible')).toBe(false);
  });

  it('test-rescheduleBuildSet', async function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail'});
    spyOn(Repository.prototype, 'start_build');
    this.view.model.set('repository', {'id': 'some-repo-id'});
    this.view.model.set('branch', 'master');
    this.view.model.set('commit', 'asdf123');
    spyOn(utils, 'showSuccessMessage');
    await this.view.rescheduleBuildSet();
    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });

  it('test-rescheduleBuildSet-error', async function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail'});
    spyOn(Repository.prototype, 'start_build').and.throwError();
    this.view.model.set('repository', {'id': 'some-repo-id'});
    this.view.model.set('branch', 'master');
    this.view.model.set('commit', 'asdf123');
    spyOn(utils, 'showErrorMessage');
    await this.view.rescheduleBuildSet();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

});


describe('BuildSetListViewTest', function(){

  beforeEach(function(){
    affix('.template .buildset-info');
    let container = $('.buildset-info');
    container.affix('.buildset-title');
    container.affix('.buildset-branch');
    container.affix('.buildset-status');
    container.affix('.buildset-commit');
    container.affix('.buildset-commit-date');
    container.affix('.buildset-started');
    container.affix('.buildset-total-time');
    container.affix('.buildset-title-container a');
    spyOn(BuildSetListView.prototype, '_connect2ws');
    this.view = new BuildSetListView('some/repo');
  });

  it('test-get_view', function(){
    let view = this.view._get_view();
    expect(view instanceof BuildSetInfoView).toBe(true);
  });
});
