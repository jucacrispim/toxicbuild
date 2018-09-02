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

var TOXIC_WATERFALL_API_URL = window.TOXIC_API_URL + 'waterfall/';


class Waterfall{

  constructor(repo_name){
    this.repo_name = repo_name;
    this.buildsets = new BuildSetList();
    this.builders = new BuilderList();
    this._api_url = TOXIC_WATERFALL_API_URL;
  }

  async fetch(){
    let url = this._api_url + '?repo_name=' + this.repo_name;
    let r = await $.ajax({url: url});
    let buildsets = r.buildsets;
    let builders = r.builders;
    this.buildsets.reset(buildsets);
    this.builders.reset(builders);
  }
}

class BaseWaterfallView extends Backbone.View{

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
    super(options);
    this.builder = options.builder;
    this.directive = {'.builder-name': 'name'};
    this.template_selector = '.template .waterfall-tr';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

  _get_kw(){
    let name = this.builder.escape('name');
    let status = this.builder.escape('status');
    return {name: name, status: status};
  }

  getRendered(){
    let compiled = super.getRendered();
    $('.builder-name', compiled).addClass(
      'builder-' + this.builder.escape('status'));
    return compiled;
  }
}


class WaterfallStepView extends BaseWaterfallView{

  constructor(options){
    super(options);
    this.step = options.step;
    this.directive = {'.step-status': 'status',
		      '.step-name': 'name'};
    this.template_selector = '.template .waterfall-step-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

  _get_kw(){
    let status = this.step.escape('status');
    let name = this.step.escape('name');
    return {status: status,
	    name: name};
  }

  getRendered(){
    let rendered = super.getRendered();
    let kw = this._get_kw();
    rendered.addClass('step-' + kw.status);
    return rendered;
  }

}

class WaterfallBuildView extends BaseWaterfallView{

  constructor(options){
    super(options);
    this.build = options.build;
    this.directive = {'.build-info-status': 'status',
		      '.build-details-link @href': 'build_details_link'};
    this.template_selector = '.template .waterfall-build-info-container';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

  _get_kw(){
    let status = this.build.escape('status');
    let build_details_link = '/build/' + this.build.get('uuid');
    return {status: status, build_details_link: build_details_link};
  }

  getRendered(){
    let rendered = super.getRendered();
    $('.build-info-row', rendered).addClass(
      'build-' + this.build.escape('status'));

    let steps = this.build.get('steps');
    for (let i in steps){
      let step = steps[i];
      let view = new WaterfallStepView({step: step});
      rendered.append(view.getRendered());
    }
    let el = $(document.createElement('td'));
    el.append(rendered);
    return el;
  }
}


class WaterfallBuildSetView extends BaseWaterfallView{

  constructor(options){
    super(options);
    this.builders = options.builders;
    this.buildset = options.buildset;
    this.directive = {'.buildset-branch': 'branch',
		      '.commit-title': 'title',
		      '.buildset-total-time': 'total_time'};
    this.template_selector = '.template .waterfall-buildset-info-container';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

  _get_kw(){
    let commit = this.buildset.escape('commit').slice(0, 8);
    let branch = this.buildset.escape('branch');
    let title = this.buildset.escape('title');
    let total_time = this.buildset.escape('total_time');
    return {commit: commit, branch: branch, title: title,
	    total_time: total_time};
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

  getRendered(){
    let self = this;

    let rendered = super.getRendered();
    let el = $(document.createElement('tr'));
    el.append(rendered);

    let builds = this.buildset.get('builds');
    let builder_builds = this._getBuilderBuids(builds);
    this.builders.each(function(builder){
      let build = builder_builds[builder.id];
      if (build){
	let view = self._getBuildView(build);
	el.append(view.getRendered());
      }else{
	el.append(document.createElement('td'));
      }
    });

    let outer = $(document.createElement('div'));
    outer.append(el);
    return outer;
  }
}


class WaterfallView extends Backbone.View{

  constructor(repo_name){
    super();
    this.repo_name = repo_name;
    this.model = new Waterfall(this.repo_name);
  }

  _renderHeader(){
    let header = '';

    this.model.builders.each(function(e){
      let view = new WaterfallBuilderView({builder: e});
      header += view.getRendered().html();
    });
    return $(header);
  }

  _renderBody(){
    let self = this;

    let body = '';
    this.model.buildsets.each(function(e){
      let view = new WaterfallBuildSetView({buildset: e,
					    builders: self.model.builders});
      body += view.getRendered().html();
    });
    return $(body);
  }

  async render(){
    await this.model.fetch();
    let header = this._renderHeader();
    let header_container = $('#waterfall-header');
    header_container.append(header);

    let body = this._renderBody();
    let body_container = $('#waterfall-body');
    body_container.append(body);

    $('.wait-toxic-spinner').hide();
    $('#waterfall-container').fadeIn(300);
  }
}
