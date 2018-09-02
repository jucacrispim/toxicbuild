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

var TOXIC_BUILDSET_API_URL = window.TOXIC_API_URL + 'buildset/';
var TOXIC_BUILD_API_URL = window.TOXIC_API_URL + 'build/';


class BuildSet extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_BUILDSET_API_URL;
    let builds  = attributes ? attributes.builds : [];
    this.attributes['builds'] = this._getBuilds(builds);
  }

  _getBuilds(builds_info){
    let builds = [];

    for (let i in builds_info){
      let build_info = builds_info[i];
      let build = new Build(build_info);
      builds.push(build);
    }
    return builds;
  }
}

class Builder extends BaseModel{

}

class Build extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_BUILD_API_URL;
    let steps = attributes ? attributes.steps : [];
    this.attributes['steps'] = this._getSteps(steps);
  }

  _getSteps(steps){
    let build_steps = new Array();
    for (let i in steps){
      let step = steps[i];
      let build_step = new BuildStep(step);
      build_steps.push(build_step);
    }
    return build_steps;
  }

}

class BuildStep extends BaseModel{

}

class BuildSetList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = BuildSet;
    this.url = TOXIC_BUILDSET_API_URL;
  }
}


class BuilderList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Builder;
    this.comparator = 'name';
  }

}

class BuildDetailsView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Build();
    super(options);
    this.directive = {'.build-status': 'status',
		      '.build-output': 'output',
		      '.build-started': 'started',
		      '.builder-name': 'builder_name',
		      '.repo-name': 'repo_name',
		      '.commit-title': 'commit_title',
		      '.commit-branch': 'commit_branch',
		      '.build-total-time': 'total_time'};

    this.model = options.model;
    this.build_uuid = options.build_uuid;
    this.template_selector = '#build-details';
    this.compiled_template = null;
    this.container_selector = '.build-details-container';
    this.container = null;
  }

  _get_kw(){
    let command = this.model.escape('command');
    let status = this.model.escape('status');
    let output = this.model.escape('output');
    let started = this.model.get('started');
    let total_time = this.model.get('total_time');
    let repo_name = _.escape(this.model.get('repository').name);
    let builder_name = _.escape(this.model.get('builder').name);
    let commit_title = this.model.escape('commit_title');
    let commit_branch = this.model.escape('commit_branch');
    return {command: command, status: status, output: output,
	    started: started, total_time: total_time,
	    repo_name: repo_name, builder_name: builder_name,
	    commit_title: commit_title, commit_branch: commit_branch};
  }

  _scrollToBottom(){
    let height = $("#build-details pre")[0].scrollHeight;
    $("html, body").animate({scrollTop: height});
  }

  _listen2events(template){
    let self = this;

    $('.follow-output', template).on('click', function(){
      self._scrollToBottom();
    });
  }

  async render(){
    await this.model.fetch({build_uuid: this.build_uuid});

    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    this._listen2events(compiled);
    let badge_class = utils.get_badge_class(kw.status);
    $('.build-status', compiled).addClass(badge_class);
    $('.obj-details-buttons-container', compiled).show();
    this.container = $(this.container_selector);
    this.container.html(compiled);
  }

}

class BuildSetInfoView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new BuildSet();
    super(options);

    this.directive = {
      '.buildset-title': 'title',
      '.buildset-branch': 'branch',
      '.buildset-status': 'status',
      '.buildset-commit': 'commit',
      '.buildset-commit-date': 'date',
      '.buildset-started': 'started',
      '.buildset-total-time': 'total_time'
    };

    this.template_selector = '.template .buildset-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

 _get_kw(){
   let title = this.model.escape('title');
   let body = this.model.escape('body');
   let status = this.model.get('status');
   let commit = this.model.get('commit');
   let date = this.model.get('commit_date');
   let branch = this.model.get('branch');
   let started = this.model.get('started');
   let finished = this.model.get('finished');
   let total_time = this.model.get('total_time');
   return {title: title, body: body, status: status, commit: commit,
	   date: date, started: started, finished: finished,
	   branch: branch, total_time: total_time};
 }

  getRendered(){
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    if (kw.started){
      $('.buildset-total-time-row', compiled).show();
    }
    let status = kw.status;
    let badge_class = utils.get_badge_class(status);
    compiled.addClass('repo-status-' + status.replace(' ', '-'));
    $('.badge', compiled).addClass(badge_class);
    return compiled;
  }
}


class BuildSetListView extends BaseListView{

  constructor(repo_name){
    let model = new BuildSetList();
    let options = {'tagName': 'ul',
		   'model': model};
    super(options);
    this._container_selector = '#obj-list-container';
    this.repo_name = repo_name;
  }

  async _fetch_items(){
    let kw = {data: {repo_name: this.repo_name,
		     summary: true}};
    await this.model.fetch(kw);
    $('.buildset-list-top-page-header-info').fadeIn(300);
  }

  _get_view(model){
    return new BuildSetInfoView({model: model});
  }
}
