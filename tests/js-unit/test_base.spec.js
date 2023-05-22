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

describe("BaseModelTest", function(){

  beforeEach(function(){
    spyOn(jQuery, 'ajax');
    this.model = new BaseModel({'id': 'some-id'});
  });

  it('test-post2api', async function(){
    $.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let url = 'http://bla.nada/';
    let body = {'some': 'data'};
    let model = new BaseModel();
    await model._post2api(url, body);
    let called = $.ajax.calls.allArgs()[0][0];
    let called_keys = [];
    for(let key in called){
      called_keys.push(key);
    }

    let expected = ['url', 'type', 'contentType', 'headers', 'data'];
    expect(called_keys).toEqual(expected);
  });

  it('test-request2api', async function(){
    $.ajax.and.returnValue(JSON.stringify({'some': 'thing'}));
    let url = 'http://bla.nada/';
    let model = new BaseModel();
    await model._post2api(url, null);
    let called = $.ajax.calls.allArgs()[0][0];
    let called_keys = [];
    for(let key in called){
      called_keys.push(key);
    }

    let expected = ['url', 'type', 'contentType', 'headers'];
    expect(called_keys).toEqual(expected);
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

  it('test-is-name-available-ok', async function(){
    let model = new BaseModel();
    model.fetch = async function(kw){return {items: []};};
    let r = await is_name_available(model, 'some-name');
    expect(r).toBe(true);
  });

  it('test-is-name-available-not-available', async function(){
    let model = new BaseModel();
    spyOn(model, 'fetch').and.returnValue({items: [{}]});
    let r = await is_name_available(model, 'some-name');
    expect(r).toBe(false);
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


describe('BaseFormViewTest', function(){

  beforeEach(function(){
    this.view = new BaseFormView();
    this.view.model = new BaseModel();
    affix('.save-btn-container button');
    affix(this.view._name_avail_s);
    affix(this.view._name_avail_indicator_s);
    affix(this.view._name_avail_spinner_s);
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
    let second_in = affix('input');
    second_in.data('valuefor', 'name');
    second_in.val('qwer');

    this.view._model_init_values = {'name': 'asfd'};

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

  it('test-getChangesFromInput-checkbox', function(){
    let input = affix('input');
    input.prop('type', 'checkbox');
    input.data('valuefor', 'bla');
    input.prop('checked', true);
    this.view._getChangesFromInput();
    expect(this.view._model_changed['bla']).toBe(true);
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

  it('test-nclearNameAvailableInfo', function(){
    this.view._clearNameAvailableInfo();
    expect(this.view._name_available.is(':visible')).toBe(false);
    expect(this.view._name_available_indicator.is(':visible')).toBe(false);
    expect(this.view._name_available_spinner.is(':visible')).toBe(false);
  });

  it('test-handleNameAvailableInfo-available', function(){
    spyOn(this.view, '_checkHasChanges');
    this.view._clearNameAvailableInfo();
    this.view._handleNameAvailableInfo(true);
    expect(this.view._name_available.html()).toEqual('');
  });

  it('test-handleNameAvailableInfo-not-available', function(){
    spyOn(this.view, '_checkHasChanges');
    this.view._clearNameAvailableInfo();
    this.view._handleNameAvailableInfo(false);
    expect(this.view._name_available.html()).toEqual('Name not available');
  });

  it('test-checkNameAvailable-same-as-init', async function(){
    this.view._model_init_values['name'] = 'init_name';
    spyOn(this.view, '_checkHasChanges');
    this.view.model.constructor.is_name_available = jasmine.createSpy('available');
    await this.view._checkNameAvailable('init_name');
    expect(this.view.model.constructor.is_name_available).not.toHaveBeenCalled();
  });

  it('test-checkNameAvailable', async function(){
    spyOn(this.view, '_checkHasChanges');
    this.view.model.constructor.is_name_available = jasmine.createSpy('available');
    await this.view._checkNameAvailable('somename');
    expect(this.view.model.constructor.is_name_available).toHaveBeenCalled();
  });

  it('test-saveChanges-error', async function(){
    spyOn(this.view.model, 'save').and.throwError();
    spyOn(utils, 'showErrorMessage');
    await this.view._saveChanges();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-saveChanges-ok', async function(){
    spyOn(this.view.model, 'save');
    spyOn(utils, 'showSuccessMessage');
    await this.view._saveChanges();
    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });

  it('test-getRemoveModal', function(){
    let self = this;
    expect(function(){self.view._getRemoveModal();}).toThrow(
      new Error('You must implement _getRemoveModal()'));
  });

  it('test-removeObj-exeption', async function(){
    spyOn(this.view.model, 'remove').and.throwError();
    spyOn(utils, 'showErrorMessage');
    let modal = jasmine.createSpy('modal');
    modal.modal = jasmine.createSpy();
    modal.on = jasmine.createSpy();
    spyOn(this.view, '_getRemoveModal').and.returnValue(modal);
    await this.view._removeObj();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-removeObj-ok', async function(){
    spyOn(this.view.model, 'remove');
    spyOn(utils, 'showSuccessMessage');
    let modal = jasmine.createSpy('modal');
    modal.modal = jasmine.createSpy();
    modal.on = jasmine.createSpy();
    spyOn(this.view, '_getRemoveModal').and.returnValue(modal);
    await this.view._removeObj();
    expect(utils.showSuccessMessage).toHaveBeenCalled();
  });
});


describe('BaseListViewTest', function(){

  beforeEach(function(){
    window.wsconsumer = jasmine.createSpy();
    this.view = new BaseListView();
    this.view.model = new BaseCollection();
  });

  it('test-get_view', function(){
    let self = this;
    let model = jasmine.createSpy();
    expect(function(){self.view._get_view(model);}).toThrow(
      new Error('You must implement _get_view()'));
  });

  it('test-fetch_items', async function(){
    let self = this;
    let model = jasmine.createSpy();
    var threw;
    try{
      await this.view._fetch_items();
      threw = false;
    }catch(e){
      threw = true;
    }
    expect(threw).toBe(true);
  });

  it('test-render_obj', function (){
    let view = jasmine.createSpy();
    let el_rendered  = $('.some-html');
    el_rendered.html('the content');
    view.getRendered = jasmine.createSpy().and.returnValue(el_rendered);
    spyOn(this.view, '_get_view').and.returnValue(view);
    let rendered = this.view._render_obj();
    expect(rendered.selector).toEqual('.some-html');
  });

  it('test-render_obj-prepend', function (){
    let view = jasmine.createSpy();
    let el_rendered  = $('.some-html');
    el_rendered.html('the content');
    view.getRendered = jasmine.createSpy().and.returnValue(el_rendered);
    spyOn(this.view, '_get_view').and.returnValue(view);
    let rendered = this.view._render_obj(jasmine.createSpy(), false);
    expect(rendered.selector).toEqual('.some-html');
  });

  it('test-render_all', async function(){
    window.wsconsumer.disconnect = jasmine.createSpy();
    window.wsconsumer.connectTo = jasmine.createSpy();
    spyOn(this.view, '_fetch_items');
    spyOn(this.view, '_render_list');
    await this.view.render_all();
    expect(this.view._fetch_items).toHaveBeenCalled();
    expect(this.view._render_list).toHaveBeenCalled();
  });

});


describe('BaseBuildDetailsViewTest', function(){
  beforeEach(function(){
    this.view = new BaseBuildDetailsView();
  });

  it('test-add2StepQueue-steps', async function(){
    let build = jasmine.createSpy();
    build.get = jasmine.createSpy();
    this.view.build = build;
    let steps = jasmine.createSpy();

    this.view._add2StepQueue(steps);
    expect(this.view.build.get).not.toHaveBeenCalled();
  });

  it('test-add2StepQueue-no-queue', function(){
    spyOn(this.view, '_addStep');
    let step = new BuildStep({uuid: 'some-uuid', index: 0});
    this.view.build.get('steps').models.push(step);
    this.view.build.get('steps').length = 1;
    this.view._add2StepQueue();
    expect(this.view._step_queue.length).toEqual(1);
  });

  it('test-add2StepQueue-greater', function(){
    spyOn(this.view, '_addStep');
    let step = new BuildStep({uuid: 'some-uuid', index: 0});
    this.view._step_queue.push(step);
    this.view.build.get('steps').models.push(step);
    step = new BuildStep({uuid: 'other-uuid', index: 1});
    this.view.build.get('steps').models.push(step);
    this.view.build.get('steps').length = 2;
    this.view._add2StepQueue();
    let last_step = this.view._step_queue[1];
    expect(this.view._step_queue.length).toEqual(2);
    expect(last_step.get('index')).toEqual(1);
  });

  it('test-add2StepQueue-lesser', function(){
    spyOn(this.view, '_addStep');
    let step = new BuildStep({uuid: 'some-uuid', index: 1});
    this.view._step_queue.push(step);
    this.view.build.get('steps').models.push(step);
    step = new BuildStep({uuid: 'other-uuid', index: 0});
    this.view.build.get('steps').models.push(step);
    this.view.build.get('steps').length = 2;
    this.view._add2StepQueue();
    let last_step = this.view._step_queue[1];
    expect(this.view._step_queue.length).toEqual(2);
    expect(last_step.get('index')).toEqual(1);
  });

  it('test-stepOk2Add-first-step', function(){
    let step = new BuildStep({index: 0});
    let ok = this.view._stepOk2Add(step);
    expect(ok).toBe(true);
  });

  it('test-stepOk2Add-step-ok', function(){
    this.view._last_step = 0;
    let step = new BuildStep({index: 1});
    let ok = this.view._stepOk2Add(step);
    expect(ok).toBe(true);
  });

  it('test-stepOk2Add-step-not-ok', function(){
    let step = new BuildStep({index: 1});
    let ok = this.view._stepOk2Add(step);
    expect(ok).toBe(false);
  });

});
