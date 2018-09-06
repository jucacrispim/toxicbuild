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

  it('test-getBuilds', function(){
    let buildset_info = {'builds': [{'steps': [{'command': 'bla'}]}]};
    let buildset = new BuildSet(buildset_info);
    expect(buildset.get('builds')[0] instanceof Build).toBe(true);
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
    this.view = new BuildSetListView('some/repo');
  });

  it('test-get_view', function(){
    let view = this.view._get_view();
    expect(view instanceof BuildSetInfoView).toBe(true);
  });
});
