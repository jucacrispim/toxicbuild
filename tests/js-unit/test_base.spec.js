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

describe("BaseModelTest", function(){

  beforeEach(function(){
    spyOn(jQuery, 'ajax');
    this.model = new BaseModel({'id': 'some-id'});
  });

  it('test-get-url-delete', function(){
    let method = 'delete';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-update', function(){
    let method = 'update';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);

  });

  it('test-get-url-read-with-id', function(){
    let method = 'read';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-create', function(){
    let method = 'create';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model, false);
    let expected = 'http://bla.com/api/';
    expect(url).toEqual(expected);
  });

  it('test-sync', async function(){
    let method = 'create';
    this.model._api_url = 'http://bla.com/api/';
    let options = {};
    await this.model.sync(method, this.model, options);
    let expected = 'http://bla.com/api/';
    expect(options.url).toEqual(expected);
  });

  it('test-parse-items', function(){
    let data = {'items': [{'bla': true}]};
    let parsed = this.model.parse(data);
    expect(parsed['bla']).toBe(true);
  });

  it('test-parse-obj', function(){
    let data = {'bla': true};
    let parsed = this.model.parse(data);
    expect(parsed['bla']).toBe(true);
  });

  it('test-fetch', function(){
    this.model.fetch({'bla': 'ble'});
    expect(this.model._has_used_query).toBe(true);
  });

  it('test-set-key-init-value', function(){
    let init = this.model.get('id');
    this.model.set('id', 'other');
    this.model.set('id', init);
    expect(this.model._changes.hasOwnProperty('id')).toBe(false);
  });

  it('test-set-key-other-value', function(){
    this.model.set('id', 'other');
    expect(this.model._changes.hasOwnProperty('id')).toBe(true);
  });

  it('test-remove', async function(){
    await this.model.remove();
    expect(jQuery.ajax).toHaveBeenCalled();
  });

});

describe('BaseCollectionTest', function(){

  beforeEach(function(){
    this.collection = new BaseCollection();
  });

  it('test-parse', function(){
    let data = {'items': [{'some': 'thing'}]};
    let expected = [{'some': 'thing'}];
    let returned = this.collection.parse(data);
    expect(returned).toEqual(expected);
  });

  it('test-sync', function(){
    window._getHeaders = jasmine.createSpy();
    let model = jasmine.createSpy('some-model');
    spyOn(Backbone, 'sync');
    this.collection.sync('post', model, {});
    expect(window._getHeaders).toHaveBeenCalled();
  });
});


describe('BaseViewTest', function(){

  beforeEach(function(){
    this.view = new BaseView();
    this.view.model = new BaseModel();
    affix('.save-btn-container button');
  });

  it('test-getChangesFromInput-different-value', function(){
    let fist_in = affix('input');
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('asfd');
    this.view._model_init_values = {'name': 'some'};
    this.view._getChangesFromInput();
    let c_count = Object.keys(this.view._model_changed).length;
    expect(c_count).toEqual(1);
  });

  it('test-getChangesFromInput-same-as-init-value', function(){
    let fist_in = affix('input');
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('asfd');
    this.view._model_init_values = {'name': 'asfd'};
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
    this.view._model_init_values = {'name': 'asfd'};
    spyOn(this.view.model, 'set');
    this.view._getChangesFromInput();
    second_in.val('asfd');
    this.view._getChangesFromInput();
    expect(this.view._model_changed.hasOwnProperty('name')).toBe(false);
  });

  it('test-getChangesFromInput-no-required-value', function(){
    let input = affix('input');
    input.prop('required', true);
    input.data('valuefor', 'bla');
    input.val('');
    this.view._getChangesFromInput();
    expect(this.view._model_changed.hasOwnProperty('bla')).toBe(false);
  });

  it('test-hasChanges', function(){
    this.view._model_changed['bla'] = false;
    expect(this.view._hasChanges()).toBe(true);
  });

  it('test-hasRequired', function(){
    var threw;
    try{
      this.view._hasRequired();
      threw = false;
    }catch(e){
      threw = true;
    }
    expect(threw).toBe(true);
  });

  it('test-checkHasChanges-changed-and-required', function(){
    spyOn(this.view, '_getChangesFromInput');
    spyOn(this.view, '_hasChanges').and.returnValue(true);
    spyOn(this.view, '_hasRequired').and.returnValue(true);
    this.view._checkHasChanges();
    let btn = jQuery('.save-btn-container button');
    expect(btn.prop('disabled')).toBe(false);
  });

  it('test-checkHasChanges-not-required', function(){
    spyOn(this.view, '_getChangesFromInput');
    spyOn(this.view.model, 'hasChanged').and.returnValue(true);
    spyOn(this.view, '_hasRequired').and.returnValue(false);
    this.view._checkHasChanges();
    let btn = jQuery('.save-btn-container button');
    expect(btn.prop('disabled')).toBe(true);
  });

  it('test-checkHasChanges-not-changed', function(){
    spyOn(this.view, '_getChangesFromInput');
    spyOn(this.view.model, 'hasChanged').and.returnValue(false);
    spyOn(this.view, '_hasRequired').and.returnValue(true);
    this.view._checkHasChanges();
    let btn = jQuery('.save-btn-container button');
    expect(btn.prop('disabled')).toBe(true);
  });

});
