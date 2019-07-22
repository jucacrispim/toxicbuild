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

var TOXIC_WATERFALL_API_URL = window.TOXIC_API_URL + 'waterfall/';

// this is here because of my lack of knowledge in js.
var _waterfall_builds = {};

class Waterfall{

  constructor(repo_name){
    this.repo_name = repo_name;
    this.buildsets = new BuildSetList();
    this.builders = new BuilderList();

    $(document).off('buildset_added');

    // unbinding the stuff from BuildSet here so we bind it to the
    // waterfall stuff.
    let self = this;
    $(document).off('build_preparing build_started build_finished');

    $(document).on(
      'build_preparing build_started build_finished build_cancelled',
      function(e, data){
	self._updateBuild(data);
	self._updateBuilder(data);
    });
    this._api_url = TOXIC_WATERFALL_API_URL;

    // we need this so we can update the builds/steps when we get a message
    // from the server
    this._builds = _waterfall_builds;
    for (let key in this._builds){
      delete this._builds[key];
    }
    this._steps = {};
    this._finished_steps_data = {};
  }

  _setWaterfallBuilds(buildsets){
    let self = this;
    _.each(buildsets, function(b){
      let builds = b.get('builds');
      _.each(builds, function(build){
	self.setBuild(build);
	let steps = build.get('steps');
	steps.each(function(step){
	  self._steps[step.get('uuid')] = step;
	});
      });
    });
  }

  _updateBuild(data){
    let build = this._builds[data.uuid];
    build.set('status', data.status);
  }

  _addStep(data){
    let build = this.getBuild(data.build.uuid);
    let steps = build.get('steps');
    let step = new BuildStep(data);
    this._steps[step.get('uuid')] = step;
    steps.add([step]);

    // checking if the step already finished
    let finished_data = this._finished_steps_data[data.uuid];
    if (finished_data){
      this._updateStep(data);
    }
  }

  _updateStep(data){
    let step = this._steps[data.uuid];
    if (!step){
      this._finished_steps_data[data.uuid] = data;
    }else{
      step.set(data);
    }
  }

  _updateBuilder(data){
    let builder_id = data.builder.id;
    let builder = this.builders.get(builder_id);
    builder.set('status', data.status);
  }

  async fetch(){
    let self = this;
    let url = this._api_url + '?repo_name=' + this.repo_name;
    let r = await $.ajax({url: url});
    let buildsets = r.buildsets;
    let builders = r.builders;
    this.buildsets.reset(buildsets, {no_events: true});
    this.buildsets.each(function(b){
      utils.setBuildsForBuildSet(b);
    });
    this._setWaterfallBuilds(this.buildsets.models);
    this.builders.reset(builders);

  }

  _getBuildsetBuilders(data){
    let builders = new Array();
    for (let i in data.builds){
      let build_dict = data.builds[i];
      let builder = new Builder(build_dict.builder);
      builders.push(builder);
    }
    return builders;
  }

  _addBuildSet(data){
    let builders = this._getBuildsetBuilders(data);
    let new_builders = new Array();
    for (let i in builders){
      let builder = builders[i];
      if (this.builders.indexOf(builder) == -1){
	this.builders.add(builder);
      }
    }

    let buildset = new BuildSet(data, {no_events: true});
    utils.setBuildsForBuildSet(buildset);
    this.buildsets.add([buildset], {at: 0});
    this._setWaterfallBuilds([this.buildsets.models[0]]);
  }

  getBuild(uuid){
    return this._builds[uuid];
  }

  setBuild(build){
    this._builds[build.get('uuid')] = build;
  }
}

class BaseWaterfallView extends BaseBuildDetailsView{

  getRendered(){
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    return compiled;
  }

}


class WaterfallBuilderView extends BaseWaterfallView{

  constructor(options){
    if (!options || !options.builder){
      throw new Error('You must pass a builder');
    }
    options.tagName = 'th';
    super(options);

    let self = this;
    this.builder = options.builder;
    this.directive = {'.builder-name': 'name'};
    this.template_selector = '.template .waterfall-tr';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    this.builder.on({change: function(){
      self.getRendered();
    }});
  }

  _get_kw(){
    let name = this.builder.escape('name');
    let status = this.builder.escape('status');
    let status_translation = i18n(status);
    return {name: name, status: status_translation,
	    original_status: status};
  }

  getRendered(){
    let compiled = super.getRendered();
    $('.builder-name', compiled).addClass(
      'builder-' + this.builder.escape('status'));
    this.$el.html($('div', compiled));
    return this;
  }
}


class WaterfallStepView extends BaseWaterfallView{

  constructor(options){
    options.tagName = 'li';
    super(options);
    let self = this;
    this.step = options.step;
    this.build_view = options.build_view;
    this.directive = {'.step-status': 'status',
		      '.step-name': 'name'};
    this.template_selector = '.template .waterfall-step-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    this.step.on({change: function(){
      self.render();
      self.build_view._addStep();
    }});
  }

  _get_kw(){
    let status = this.step.escape('status');
    let status_translation = i18n(status);
    let name = this.step.escape('name');
    return {status: status_translation,
	    original_status: status,
	    name: name};
  }

  render(){
    let rendered = super.getRendered();
    let kw = this._get_kw();
    rendered.addClass('step-' + kw.original_status);
    this.$el.removeClass();
    this.$el.addClass('step-' + kw.original_status + ' build-info-row');
    this.$el.html(rendered.html());
    return this;
  }

  getRendered(){
    return this.render().$el;
  }

}


class WaterfallBuildView extends BaseWaterfallView{

  constructor(options){
    options.tagName = 'td';
    super(options);
    let self = this;
    this.build = options.build;
    this.directive = {'.build-info-status': 'status',
		      '.build-details-link @href': 'build_details_link',
		      '.build-info-number': 'number'};
    this.template_selector = '.template .waterfall-build-info-container';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    this.build.on({'change': function(){
      self.reRenderInfo();
    }});

    this.build.get('steps').on({'add': function(){
      self._add2StepQueue();
    }});

    this._last_step = null;
    this.__add_step_lock = null;
  }

  _get_kw(){
    let status = this.build.escape('status');
    let status_translation = i18n(status);
    let number = this.build.get('number');
    let build_details_link = '/build/' + this.build.get('uuid');
    return {status: status_translation,
	    original_status: status,
	    build_details_link: build_details_link,
	    number: number};
  }

  async _addStep(){
    let self = this;

    while (this.__add_step_lock){
      await utils.sleep(200);
    }
    this.__add_step_lock = true;
    let step = this._step_queue[0];

    if (!step || !this._stepOk2Add(step)){
      this.__add_step_lock = null;
      return false;
    }
    this._step_queue.shift();
    let view = new WaterfallStepView({step: step, build_view: self});
    let rendered = view.getRendered();
    $('ul', this.$el).append(rendered);
    let el = $('li', this.$el)[$('li', this.$el).length - 1];

    let cb = function(){
      self.__add_step_lock = null;
      self._last_step = step.get('index');
    };
    utils.wrapperSlideDown($(el), 600, cb);
    return true;
  }

  reRenderInfo(){
    let status = this.build.get('status');
    let el = $($('.build-info-row', this.$el)[0]);
    el.removeClass();
    el.addClass('build-info-row build-' + status);
    $('.build-info-status', el).text(i18n(status));
    this._handleCancelButton(el, status);
    this._handleRunningCog(el, status);
  }

  _handleCancelButton(rendered, status){
    var cancel_statuses = ['pending'];
    if (cancel_statuses.indexOf(status) >= 0){
      $('.fa-times', rendered).show();
    }else{
      $('.fa-times', rendered).hide();
    }
  }

  _handleRunningCog(rendered, status){
    if (status == 'running' || status == 'preparing'){
      $('.fa-cog', rendered).prop('style', 'display: inline-block');
    }else{
      $('.fa-cog', rendered).hide();
    }
  }

  render(){
    let self = this;

    let status = this.build.escape('status');
    let rendered = super.getRendered();
    $('.build-info-row', rendered).addClass(
      'build-' + status);

    let steps = this.build.get('steps');
    steps.each(function(step){
      let view = new WaterfallStepView({step: step, build_view: self});
      rendered.append(view.getRendered());
      self._last_step = step.get('index');
    });

    this._handleCancelButton(rendered, status);
    this._handleRunningCog(rendered, status);

    this.$el.html('');
    this.$el.append(rendered);
    router.setUpLinks(this.$el);

    $('.fa-redo', this.$el).on('click', function(){
      let builder_name = self.build.get('builder').name;
      utils.rescheduleBuildSet(self.build, self.$el, builder_name);
    });

    $('.fa-times', this.$el).on('click', function(){
      self.cancelBuild();
    });
  }

  async cancelBuild(){
    let spinner = $('.spinner-reschedule-buildset', this.$el);
    let repo = new Repository({id: this.build.get('repository').id});
    let build_uuid = this.build.get('uuid');
    spinner.show();
    let btn = $('.fa-times', this.$el);
    btn.hide();
    try{
      await repo.cancel_build(build_uuid);
      utils.showSuccessMessage(i18n('Build canceled'));
    }catch(e){
      utils.showErrorMessage(i18n('Error canceling build'));
      btn.show();
    }
    spinner.hide();
  }

  getRendered(){
    this.render();
    return this.$el;
  }
}


class WaterfallBuildSetView extends BaseWaterfallView{

  constructor(options){
    options = options || {};
    options.tagName = 'tr';
    super(options);
    let self = this;

    this.builders = options.builders;
    this.buildset = options.buildset;
    this.directive = {'.buildset-branch': 'branch',
		      '.commit-title': 'title',
		      '.buildset-details-link @href': '/buildset/#{id}',
		      '.buildset-total-time': 'total_time'};
    this.template_selector = '.template .waterfall-buildset-info-container';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    this.counter = new TimeCounter();

    this.buildset.on({change: function(){
      self.reRenderInfo();
    }});
  }

  _get_kw(){
    let id = this.buildset.get('id');
    let commit = this.buildset.escape('commit').slice(0, 8);
    let branch = this.buildset.escape('branch');
    let title = this.buildset.escape('title');
    let total_time = this.buildset.escape('total_time');
    return {commit: commit, branch: branch, title: title,
	    total_time: total_time, id: id};
  }

  _getBuilderBuids(builds){
    let builder_builds = builds.reduce(function(obj, build){
      let builder = build.get('builder');
      obj[builder.id] = build;
      return obj;
    }, {});
    return builder_builds;
  }

  _getBuildView(build){
    return new WaterfallBuildView({build: build});
  }

  reRenderInfo(){
    let self = this;

    let rendered = super.getRendered();
    let first_col = $('.waterfall-first-col', this.$el);
    first_col.html(rendered.html());
    $('.fa-redo', first_col).on('click', function(){
      utils.rescheduleBuildSet(self.buildset, first_col);
    });

    router.setUpLinks(first_col);

    if (!this.buildset.get('finished')){
      let self = this;

      let cb = function(secs){
	let f = utils.formatSeconds(secs);
	let el = $('.buildset-total-time', self.$el);
	el.text(f);
      };

      this.counter.start(cb);
    }else{
      this.counter.stop();
    }

  }

  getRendered(){
    let self = this;

    let rendered = super.getRendered();
    this.$el.append(rendered);

    let builds = this.buildset.get('builds');
    let builder_builds = this._getBuilderBuids(builds);
    this.builders.each(function(builder){
      let build = builder_builds[builder.id];
      if (build){
	build.set('repository', self.buildset.get('repository'));
	let view = self._getBuildView(build);
	self.$el.append(view.getRendered());
      }else{
	self.$el.append(document.createElement('td'));
      }
    });

    let first_col = $('.waterfall-first-col', this.$el);
    $('.fa-redo', first_col).on('click', function(){
      utils.rescheduleBuildSet(self.buildset, first_col);
    });

    return this;
  }
}


class WaterfallView extends Backbone.View{

  constructor(repo_name){
    super();
    let self = this;
    this.repo_name = repo_name;
    this.model = new Waterfall(this.repo_name);
    this.model.buildsets.on({'add': function(){
      self._addNewBuilders();
      self._addNewBuildSet();
    }});

    $(document).on('step_started', function(e, data){
      self.model._addStep(data);
    });

    $(document).on('step_finished', function(e, data){
      self.model._updateStep(data);
    });

    $(document).on('buildset_added', function(e, data){
      self.model._addBuildSet(data);
    });

  }

  _renderHeader(){
    let header_container = $('#waterfall-header');

    this.model.builders.each(function(e){
      let view = new WaterfallBuilderView({builder: e});
      let el = view.getRendered().$el;
      header_container.append(el);
    });
  }

  _renderBody(){
    let self = this;

    let body_container = $('#waterfall-body');
    this.model.buildsets.each(function(e){
      let view = new WaterfallBuildSetView({buildset: e,
					    builders: self.model.builders});
      body_container.append(view.getRendered().$el);
    });
  }

  _addBuilder2Header(builder, insert_index){
    let header_container = $('#waterfall-header');
    let builder_view = new WaterfallBuilderView({builder: builder});
    let el = builder_view.getRendered().$el;

    header_container.children().eq(insert_index).after(el);
  }

  _addBuilderColumn(insert_index){
    let self = this;

    let body_container = $('#waterfall-body');
    $('tr', body_container).each(function(i, e){
      e.children().eq(insert_index).after('<td class="build-placeholder"></td>');
    });
  }

  _addNewBuilder(builder, builder_names){
    let insert_index = -1 * utils.binarySearch(builder_names, builder.get('name'));
    this._addBuilder2Header(builder, insert_index);
    this._addBuilderColumn(insert_index);
  }

  _addNewBuilders(){
    let self = this;

    let builder_els = $('.builder-name').slice(1);
    let builder_names = [];
    builder_els.map(function(i, e){builder_names.push($(e).html());});
    this.model.builders.each(function(e){
      let name = e.get('name');

      if (builder_names.indexOf(name) < 0){
	self._addNewBuilder(e, builder_names);
      }
    });
  }

  _addNewBuildSet(){
    let body_container = $('#waterfall-body');
    let buildset = this.model.buildsets.models[0];
    let view = new WaterfallBuildSetView({buildset: buildset,
					  builders: this.model.builders});
    let view_el = view.getRendered().$el;
    body_container.prepend(view_el.hide().fadeIn(700));

    // so, this mess here is to slideDown the table row.
    // tks to `wiks` on stackoverflow!!
    let tags = ['td', 'th'];
    for (let i in tags){
      let tag = tags[i];
      let el = view_el.find(tag);
      utils.wrapperSlideDown(el, 600);
    }
  }

  _connect2ws(){
    let repo_name = $('#repo_name').val();
    let path = 'waterfall-info?repo_name=' + repo_name;
    wsconsumer.connectTo(path);
  }

  async render(){
    await this.model.fetch();
    this._renderHeader();
    this._renderBody();
    this._connect2ws();
    $('.wait-toxic-spinner').hide();
    $('#waterfall-container').fadeIn(300);
  }
}
