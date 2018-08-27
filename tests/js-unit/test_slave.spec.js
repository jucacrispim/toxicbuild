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

describe('SlaveTest', function(){

  beforeEach(function(){
    this.model = new Slave();
  });

  it('test-is-name-available', async function(){
    let r = await Slave.is_name_available('some-name');
    expect(r).toBe(true);
  });
});

describe('BaseSlaveViewTest', function(){

  beforeEach(function(){
    this.view = new BaseSlaveView();
  });

  it('test-get_kw', function(){
    let model = new Slave({name: 'someslave', host: 'somewhere', port: 1234});
    this.view.model = model;
    let kw = this.view._get_kw();
    expect(kw.name).toEqual('someslave');
  });

});

describe('SlaveInfoViewTest', function(){
  beforeEach(function(){
    let container_selector = '.template .slave-info';
    affix(container_selector);
    let container = $(container_selector);
    container.affix('.slave-info-name');
    container.affix('.slave-details-link');
    container.affix('.slave-info-host');
    container.affix('.slave-info-port');
    this.view = new SlaveInfoView();
  });

  it('test-getRendered', function(){
    let compiled = this.view.getRendered();
    expect(Boolean(compiled)).toBe(true);
  });
});

describe('SlaveListViewTest', function(){

  beforeEach(function(){
    this.view = new SlaveListView();
    affix('#slave-list-container');
    affix('.wait-toxic-spinner');
    affix('.top-page-slaves-info-container');
  });

  it('test-render_list', function(){
    spyOn(this.view, '_render_obj');
    this.view.model.add([{}]);
    this.view._render_list();
    expect(this.view._render_obj).toHaveBeenCalled();
  });

});

describe('BaseSlaveDetailsViewTest', function(){

  beforeEach(function(){
    this.view = new BaseSlaveDetailsView({name: 'someslave'});
    let container = affix(this.view.template_selector);
    affix(this.view.container_selector);
    container.affix('input.slave-details-name');
    container.affix('input.slave-details-host');
    container.affix('input.slave-details-port');
    container.affix('input.slave-details-token');
    container.affix('checkbox.slave-details-use-ssl');
    container.affix('checkbox.slave-details-verify-cert');
  });

  it('test-hasRequired-no-name', function(){
    $('.slave-details-name').val();
    $('.slave-details-host').val('some.host');
    $('.slave-details-port').val(1234);
    $('.slave-details-token').val('bla');

    let has_required = this.view._hasRequired();
    expect(has_required).toBe(false);
  });

  it('test-hasRequired-no-host', function(){
    $('.slave-details-name').val('asdf');
    $('.slave-details-host').val('');
    $('.slave-details-port').val(1234);
    $('.slave-details-token').val('bla');

    let has_required = this.view._hasRequired();
    expect(has_required).toBe(false);
  });

  it('test-hasRequired-no-port', function(){
    $('.slave-details-name').val('asdf');
    $('.slave-details-host').val('some.host');
    $('.slave-details-port').val();
    $('.slave-details-token').val('bla');

    let has_required = this.view._hasRequired();
    expect(has_required).toBe(false);
  });

  it('test-hasRequired-no-token', function(){
    $('.slave-details-name').val('asdf');
    $('.slave-details-host').val('some.host');
    $('.slave-details-port').val(1234);
    $('.slave-details-token').val('');

    let has_required = this.view._hasRequired();
    expect(has_required).toBe(false);
  });

  it('test-hasRequired-ok', function(){
    $('.slave-details-name').val('asdf');
    $('.slave-details-host').val('some.host');
    $('.slave-details-port').val(1234);
    $('.slave-details-token').val('bla');

    let has_required = this.view._hasRequired();
    expect(has_required).toBe(true);
  });
});

describe('SlaveDetailsViewTest', function(){

  beforeEach(function(){
    this.view = new SlaveDetailsView({name: 'someslave'});
    let container = affix(this.view.template_selector);
    affix(this.view.container_selector);
    container.affix('input.slave-details-name');
    container.affix('input.slave-details-host');
    container.affix('input.slave-details-port');
    container.affix('input.slave-details-token');
    container.affix('checkbox.slave-details-use-ssl');
    container.affix('checkbox.slave-details-verify-cert');
  });

  it('test-render_details', async function(){
    affix('.wait-toxic-spinner');
    spyOn(this.view.model, 'fetch');
    await this.view.render_details();
    let called = this.view.model.fetch.calls.allArgs()[0][0];
    expect(called['name']).toEqual('someslave');
  });

});


describe('SlaveAddViewTest', function(){

  beforeEach(function(){
    this.view = new SlaveAddView();
    let container = affix(this.view.template_selector);
    affix(this.view.container_selector);
    container.affix('input.slave-details-name');
    container.affix('input.slave-details-host');
    container.affix('input.slave-details-port');
    container.affix('input.slave-details-token');
    container.affix('checkbox.slave-details-use-ssl');
    container.affix('checkbox.slave-details-verify-cert');
  });

  it('test-render_details', function(){
    affix('.delete-btn-container');
    this.view.render_details();
    let el = $('.delete-btn-container');
    expect(el.is('visible')).toBe(false);
  });

  it('test-addSlave-ok', async function(){
    spyOn($.fn, 'trigger');
    spyOn(this.view.model, 'save').and.returnValue({full_name: 'full/some-name'});
    spyOn(utils, 'showSuccessMessage');
    this.view._model_changed = {'name': 'some-name'};
    await this.view._addSlave();
    expect(this.view.model.get('name')).toEqual('some-name');
    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });

  it('test-addSlave-exception', async function(){
    spyOn(this.view.model, 'save').and.throwError();
    spyOn(utils, 'showErrorMessage');
    this.view.model._model_changed = {name: 'some-name'};
    await this.view._addSlave();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

});
