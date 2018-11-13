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

describe('WaterfallTest', function(){

  beforeEach(function(){
    this.waterfall = new Waterfall();
    spyOn($, 'ajax');
  });

  it('test-fetch', async function(){
    $.ajax.and.returnValue({buildsets: [{}],
			    builders: [{}]});
    await this.waterfall.fetch();
    expect(this.waterfall.buildsets.length).toEqual(1);
    expect(this.waterfall.builders.length).toEqual(1);
  });

  it('test_getBuildsetBuilders', async function(){
    let data = {builds: [{builder: {name: 'builder0', id: 'id0'}},
			 {builder: {name: 'builder1', id: 'id1'}}]};
    let builders = this.waterfall._getBuildsetBuilders(data);
    expect(builders.length).toEqual(2);
  });

  it('test-setWaterfallBuilds', function(){
    let self = this;

    let build = new Build({uuid: 'bla'});
    this.waterfall.buildsets.reset([{builds: [build]}]);
    this.waterfall._setWaterfallBuilds(this.waterfall.buildsets.models);

    let has_keys = function(){
      for (let k in self.waterfall._builds){
	return true;
      }
      return false;
    }();
    expect(has_keys).toBe(true);
  });
});

describe('WaterfallBuilderViewTest', function(){

  beforeEach(function(){
    affix('.template .waterfall-tr');
    let template = $('.waterfall-tr');
    template.affix('.builder-name');
    let builder = new Builder();
    this.view = new WaterfallBuilderView({builder: builder});
  });

  it('test-constructor-without-buildset', function(){

    expect(function(){new WaterfallBuilderView();}).toThrow(
      new Error('You must pass a builder'));
  });

  it('test-getRendered', function(){
    let r = this.view.getRendered();
    expect(Boolean(r.$el.html().length)).toBe(true);
  });

});

describe('WaterfallStepViewTest', function(){
  beforeEach(function(){
    affix('.template .waterfall-step-info');
    let template = $('.waterfall-step-info');
    template.affix('.step-status');
    template.affix('.step-name');
    let step = new BuildStep();
    let build_view = jasmine.createSpy();
    build_view._addStep = jasmine.createSpy();
    this.view = new WaterfallStepView({step: step,
				       build_view: build_view});
  });

  it('test-getRendered', function(){
    this.view.step.set('status', 'running');
    let rendered = this.view.getRendered();
    expect(rendered.hasClass('step-running')).toBe(true);
  });

});


describe('WaterfallBuildViewTest', function(){

  beforeEach(function(){
    affix('.template .waterfall-step-info');
    let template = $('.waterfall-step-info');
    template.affix('.step-status');
    template.affix('.step-name');
    affix('.template .waterfall-build-info-container');
    template = $('.waterfall-build-info-container');
    template.affix('.build-info-number');
    template.affix('.build-info-status');
    template.affix('.build-info-row');
    template.affix('.build-details-link');
    let build = new Build();
    this.view = new WaterfallBuildView({build: build});
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

  it('test-addStep', async function(){
    spyOn(this.view, '_stepOk2Add').and.returnValue(true);
    this.view.$el = $('<td><ul></ul></td>');
    let step = new BuildStep({uuid: 'some-uuid'});
    this.view._step_queue.push(step);
    this.view.build.get('steps').add([step]);

    let timeout = 100;
    let i = 0;
    while (this.view.__add_step_lock && i < timeout){
      await utils.sleep(10);
      i += 1;
    }
    expect($('li', this.view.$el).length).toEqual(1);
    expect(this.view.__add_step_lock).toBe(null);
  });

  it('test-addStep-locked', async function(){
    spyOn(utils, 'sleep');
    let self = this;
    utils.sleep = function(p){self.view.__add_step_lock = null;};
    this.view.$el = $('<td><ul></ul></td>');
    let step = new BuildStep({uuid: 'some-uuid'});
    this.view.__add_step_lock = true;
    this.view.build.get('steps').add([step]);

    let timeout = 100;
    let i = 0;

    while (this.view.__add_step_lock && i < timeout){
      await utils.sleep(10);
      i += 1;
    }

    expect(this.view.__add_step_lock).toBe(null);
  });

  it('test-addStep-not-ok', async function(){
    spyOn(this.view, '_stepOk2Add').and.returnValue(false);
    this.view._step_queue[0] = jasmine.createSpy();
    let r = await this.view._addStep();
    expect(r).toBe(false);
  });

  it('test-addStep-no-step', async function(){
    spyOn(this.view, '_stepOk2Add').and.returnValue(true);
    let r = await this.view._addStep();
    expect(r).toBe(false);
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

  it('test-reRenderInfo', function(){
    this.view.$el.affix('li.build-info-row');
    let el = $('li.build-info-row', this.view.$el);
    this.view.build.set('status', 'success');
    el.affix('.build-info-status');
    el = $('li.build-info-row', this.view.$el);

    let txt_el = $('.build-info-status', this.view.$el);
    txt_el.text('fail');
    this.view.reRenderInfo();
    txt_el = $('.build-info-status', this.view.$el);
    expect(txt_el.text()).toEqual('success');
  });

  it('test-getRendered', function(){
    this.view.build.set('status', 'fail');
    let rendered = this.view.getRendered();
    let el = $('.build-info-row', rendered);
    expect(el.hasClass('build-fail')).toBe(true);
  });
});

describe('WaterfallBuildSetViewTest', function(){

  beforeEach(function(){
    affix('.template .waterfall-buildset-info-container');
    let template = $('.waterfall-buildset-info-container');
    template.affix('.buildset-commit');
    template.affix('.buildset-details-link');
    template.affix('.buildset-branch');
    template.affix('.commit-title');
    template.affix('.buildset-total-time');
    let buildset = new BuildSet();
    let builders = new BuilderList();
    this.view = new WaterfallBuildSetView({buildset: buildset,
					   builders: builders});
  });

  it('test-getRendered-builder-ok', function(){
    let view = jasmine.createSpy();
    view.getRendered = jasmine.createSpy();

    let builds = new Backbone.Collection();
    builds.add({'a': 1, builder: {id: 'bla'}});
    this.view.buildset.set('builds', builds);

    let builders = new Backbone.Collection();
    builders.add({'id': 'bla'});
    this.view.builders =  builders;

    spyOn(this.view, '_getBuildView').and.returnValue(view);
    let rendered = this.view.getRendered();
    expect(view.getRendered).toHaveBeenCalled();
  });

  it('test-getRendered-builder-not-ok', function(){
    let view = jasmine.createSpy();
    view.getRendered = jasmine.createSpy();

    let builds = new Backbone.Collection();
    builds.add({'a': 1, builder: {id: 'bla'}});
    this.view.buildset.set('builds', builds);

    let builders = new Backbone.Collection();
    this.view.builders =  builders;

    spyOn(this.view, '_getBuildView').and.returnValue(view);
    let rendered = this.view.getRendered();
    expect(view.getRendered).not.toHaveBeenCalled();
  });

  it('test-getBuilderBuilds', function(){
    let builds = new Backbone.Collection();
    builds.add({builder: {'id': 'some-id'}, 'val': 1});
    builds.add({builder: {'id': 'other-id'}, 'val': 2});
    let builder_builds = this.view._getBuilderBuids(builds);
    expect(builder_builds['some-id'].get('val')).toEqual(1);
  });

});


describe('WaterfallViewTest', function(){

  beforeEach(function(){
    affix('#waterfall-header');
    affix('#waterfall-body');
    affix('.template .waterfall-tr');
    let template = $('.waterfall-tr');
    template.affix('.builder-name');
    let el = template.affix('.waterfall-buildset-info-container');
    el.affix('.buildset-branch');
    el.affix('.commit-title');
    el.affix('.buildset-details-link');
    el.affix('.buildset-total-time');

    this.view = new WaterfallView('some/repo');
  });

  it('test-addStep', function(){
    let data = {'uuid': 'some-uuid', build: {uuid: 'build-uuid'}};
    let build = new Build({uuid: 'build-uuid'});
    this.view.model._builds[build.get('uuid')] = build;
    spyOn(BuildStepList.prototype, 'add');
    this.view._addStep(data);
    expect(BuildStepList.prototype.add).toHaveBeenCalled();
  });

  it('test-updateStep', function(){
    let data = {'uuid': 'some-uuid'};
    let step = new BuildStep(data);
    this.view.model._steps[data.uuid] = step;
    let new_data = {uuid: 'some-uuid', status: 'fail'};
    this.view._updateStep(new_data);
    expect(step.get('status')).toEqual('fail');
  });

  it('test-renderHeader', function(){
    this.view.model.builders.add({'name': 'bla'});
    this.view._renderHeader();
    let header = $('#waterfall-header');
    expect(header.length).toEqual(1);
  });

  it('test-renderBody', function(){
    this.view.model.buildsets.add({'repository': {}, builds: []});
    this.view._renderBody();
    let body = $('#waterfall-body');
    expect(body.length).toEqual(1);
  });

  it('test-addNewBuilders', function(){
    let el = affix('.builder-name');
    el.html('builder-0');
    el = affix('.builder-name');
    el.html('builder-1');

    this.view.model.builders.reset([{name: 'builder-0'},
				    {name: 'builder-1'},
				    {name: 'builder-2'}]);

    this.view._addNewBuilder = jasmine.createSpy();

    this.view._addNewBuilders();

    expect(this.view._addNewBuilder).toHaveBeenCalled();
  });

  it('test-addNewBuilders-no-new-builders', function(){
    let el = affix('.builder-name');
    el.html('builder-0');
    el = affix('.builder-name');
    el.html('builder-1');

    this.view.model.builders.reset([{name: 'builder-0'},
				    {name: 'builder-1'}]);

    this.view._addNewBuilder = jasmine.createSpy();

    this.view._addNewBuilders();

    expect(this.view._addNewBuilder).not.toHaveBeenCalled();
  });

  it('test-addBuilder2Header', function(){
    let el =  $('#waterfall-header');
    el.append('<th>first-col</th>');
    el.append('<th class="builder-name">builder-0</th>');
    el.append('<th class="builder-name">builder-2</th>');

    let builder = new Builder({name: 'builder-1'});
    let builder_names = ['builder-0', 'builder-2'];
    let insert_index = -1 * utils.binarySearch(builder_names, builder.get('name'));
    this.view._addBuilder2Header(builder, insert_index);
    let header = $('#waterfall-header');
    expect(header.html().indexOf('builder-1') >= 0).toBe(true);
  });

  it('test-addBuilderColumn', function(){
    let el = $('#waterfall-body');
    el.append('<th>first</th>');
    el.append('<td></td>');
    el.append('<td></td>');

    this.view._addBuilderColumn(1);
    el = $('#waterfall-body');

    let placeholder = $('.build-placeholder', el);
    expect(el.length).toEqual(1);
  });

  it('test-addNewBuildSet', function(){
    let build = new Build({uuid: 'asdf', builder: {id: '123'}});
    this.view.model.buildsets.add([{builds: [build]}]);
    spyOn(jQuery.fn, 'prepend');
    this.view._addNewBuildSet();
    expect(jQuery.fn.prepend).toHaveBeenCalled();
  });

  it('test-render', async function(){
    spyOn(this.view.model, 'fetch');
    spyOn(this.view, '_renderHeader');
    spyOn(this.view, '_renderBody');
    wsconsumer = jasmine.createSpy();
    wsconsumer.connectTo = jasmine.createSpy();
    await this.view.render();
    expect(this.view._renderHeader).toHaveBeenCalled();
    expect(this.view._renderBody).toHaveBeenCalled();
  });

});
