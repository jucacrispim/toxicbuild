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

var TOXIC_BUILDSET_API_URL = window.TOXIC_API_URL + 'buildset/';
var TOXIC_BUILD_API_URL = window.TOXIC_API_URL + 'build/';
var TOXIC_STEP_API_URL = window.TOXIC_API_URL + 'step/';


class BuildSet extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_BUILDSET_API_URL;
    let builds  = this.attributes ? this.attributes.builds : [];
    let self = this;
    if (!options || (options && !options.no_events)){
      $(document).on('build_preparing build_started build_finished',
		     function(e, data){
	self._updateBuild(data);
      });
    }
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

  _getBuild(uuid){
    let builds = this.get('builds');
    for (let i in builds){
      let build = builds[i];
      if (build.get('uuid') == uuid){
	return build;
      }
    }
    throw new Error('No Build ' + uuid);
  }

  _updateBuild(data){
    let build = this._getBuild(data.uuid);
    build.set('status', data.status);
  }
}

class Builder extends BaseModel{

}

class Build extends BaseModel{

  constructor(attributes, options){
    options = options || {};
    options.idAttribute = 'uuid';
    let steps = attributes && attributes.steps ? attributes.steps : [];

    super(attributes, options);

    let new_steps = this._getSteps(steps);

    this._api_url = TOXIC_BUILD_API_URL;

    this.set('steps', new_steps);
  }

  _getSteps(steps){
    let build_steps = new Array();
    for (let i in steps){
      let step = steps[i];
      let build_step = new BuildStep(step);
      build_steps.push(build_step);
    }
    let steps_list = new BuildStepList();
    steps_list.reset(build_steps);
    return steps_list;
  }

}

class BuildStep extends BaseModel{

  constructor(attributes, options){
    options = options || {};
    options.idAttribute = 'uuid';
    super(attributes, options);
    this._api_url = TOXIC_STEP_API_URL;
  }

}

class BuildStepList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = BuildStep;
  }
}

class BuildSetList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    let self = this;
    this.model = BuildSet;
    this.url = TOXIC_BUILDSET_API_URL;

    $(document).on('buildset_added', function(e, data){
      self.add(data);
    });

    $(document).on('buildset_started buildset_finished', function(e, data){
      self.updateBuildSet(data);
    });
  }

  updateBuildSet(data){
    let buildset = this.get(data.id);
    if (!buildset){
      return false;
    }
    buildset.set(data);
    return true;
  }
}


class BuilderList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Builder;
    this.comparator = 'name';
  }

}


class BuildStepDetailsView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new BuildStep();
    super(options);
    let self = this;

    this.directive = {'.step-status': 'status',
		      '.step-started': 'started',
		      '.step-total-time': 'total_time',
		      '.step-command': 'command'};

    this.model = this.step = options.model;
    this.step_uuid = options.step_uuid;
    this.page = options.page;
    this.template_selector = '#step-details';
    this.compiled_template = null;
    this.container_selector = '.step-details-container';
    this.container = null;
    this._compiled_html = null;
    this.term = null;

    this._scroll = false;

    $(document).on('step_output_info', function(e, data){
      self._addStepOutput(data);
    });

    $(document).on('step_finished', function(e, data){
      self._reRenderFinished(data);
    });

  }

  _get_kw(){
    let status = this.model.get('status');
    let status_translation = i18n(status);
    let kw = {
      status: status_translation,
      original_status: status,
      started: this.model.get('started'),
      total_time: this.model.get('total_time'),
      command: this.model.get('command'),
    };
    return kw;
  }

  setSetpOutput(output){
    let model_output = this.model.get('output') || '';
    model_output += output;
    this.model.set('output', model_output);

  }

  _addStepOutput(data){
    let step_uuid = data['uuid'];
    if (step_uuid != this.step_uuid){
      return false;
    }

    this.setSetpOutput(data.output);
    this.term.write(data.output);

    if (this._scroll){
      utils.scrollToBottom();
    }
    return true;
  }

  _reRenderFinished(data){
    if (data.uuid != this.step_uuid){
      return false;
    }
    this.model.set('status', data.status);
    this.model.set('output', data.output);
    this.model.set('total_time', data.total_time);
    this.render(false);
    return true;
  }

  async render(fetch=true){
    let self = this;
    if (fetch){
      await this.model.fetch({step_uuid: this.step_uuid});
      let repo = this.model.get('repository');
      let uuid = this.model.get('uuid');
      let path = 'step-info?repo_id=' + repo.id + '&uuid=' + uuid;
      wsconsumer.connectTo(path);
    }

    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();
    let compiled = this._compiled_html = $(this.compiled_template(kw));
    let badge_class = utils.get_badge_class(kw.original_status);
    $('.step-status', compiled).removeClass().addClass(
      'step-status badge ' + badge_class);
    $('.obj-details-buttons-container', compiled).show();
    this.container = $(this.container_selector);
    this.container.html(compiled);

    $('.follow-output', this.container).on('click', function(){
      utils.scrollToBottom();
      self._scroll = true;
    });

    if (!fetch){
      this.page._listen2events();
    }

    this.renderTerminal();
  }

  renderTerminal(){
    let el = document.getElementsByClassName('step-output')[0];
    this.term = new Terminal(el);
    let output = this.model.get('output');
    this.term.write(output);
  }
}


class BuildDetailsView extends BaseBuildDetailsView{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new Build();
    super(options);
    this._started_steps = [];
    this._finished_steps = [];
    this._output_queue = {};

    let self = this;

    this.directive = {'.build-status': 'status',
		      '.build-started': 'started',
		      '.builder-name': 'builder_name',
		      '.repo-name': 'repo_name',
		      '.build-number': 'build_number',
		      '.commit-author': 'commit_author',
		      '.commit-title': 'commit_title',
		      '.commit-branch': 'commit_branch',
		      '.build-total-time': 'total_time'};

    this.model = this.build = options.model;
    this.build_uuid = options.build_uuid;
    this.page = options.page;
    this.template_selector = '#build-details';
    this.compiled_template = null;
    this.container_selector = '.build-details-container';
    this.container = null;
    this.term = null;


    this._scroll = false;

    $(document).on('build_preparing build_started build_finished',
		   function(e, data){
      self._renderStatusChange(data);
    });

    $(document).on('step_output_info', function(e, data){
      self._add2OutputQueue(data);
    });

    let steps = this.model.get('steps');

    $(document).on('step_started', function(e, data){
      if (data.build.uuid != self.build_uuid){
	return;
      }
      let step = new BuildStep(data);
      steps.add([step]);
    });

    steps.on({'add': function(){
      self._add2StepQueue(steps);
    }});
  }

  async _addStep(){

    let step = this._step_queue[0];

    if (!step || !this._stepOk2Add(step)){
      return false;
    }

    this._step_queue.shift();

    let output_el = $('.build-output');
    let command = step.get('command') + '\n';
    output_el.append(command);

    this._last_step = step.get('index');
    this._started_steps.push(step.get('uuid'));
    this.setOutput(command);
    this._addStepOutput(step.get('uuid'));

    return true;
  }

  setOutput(output_line){
    let output = this.build.get('output') || '';
    output += output_line;
    this.build.set('output', output);
  }

  _add2OutputQueue(data){
    let step_uuid = data.uuid;
    let queue = this._output_queue[step_uuid];
    if (!queue){
      queue = [];
      this._output_queue[step_uuid] = queue;
    }

    queue.push(data);
    this._addStepOutput(step_uuid);
  }

  _addStepOutput(step_uuid){

    if (this._started_steps.indexOf(step_uuid) < 0){
      return false;
    }

    let output_queue = this._output_queue[step_uuid];

    if (!output_queue){
      return false;
    }

    let output = output_queue.shift();
    while (output){
      let output_line = output.output;
      this.setOutput(output_line);
      this.term.write(output_line);
      output = output_queue.shift();
    }

    if(this._scroll){
      this._scrollToBottom();
    }

    return true;
  }

  _renderStatusChange(data){
    if (data.uuid != this.build_uuid){
      return;
    }
    this.model.set('status', data.status);
    this.model.set('started', data.started);
    this.model.set('finished', data.finished);
    this.model.set('total_time', data.total_time);
    this.render(false);
  }

  _get_kw(){
    let command = this.model.escape('command');
    let status = this.model.escape('status');
    let status_translation = i18n(status);
    let started = this.model.get('started');
    let total_time = this.model.get('total_time');
    let repo_name = _.escape(this.model.get('repository').name);
    let builder_name = _.escape(this.model.get('builder').name);
    let commit_title = this.model.escape('commit_title');
    let commit_branch = this.model.escape('commit_branch');
    let build_number = this.model.get('number');
    let commit_author = this.model.escape('commit_author');
    return {command: command, status: status_translation,
	    'original_status': status,
	    started: started, total_time: total_time,
	    build_number: build_number,
	    repo_name: repo_name, builder_name: builder_name,
	    commit_title: commit_title, commit_branch: commit_branch,
	    commit_author: commit_author};
  }

  _scrollToBottom(){
    utils.scrollToBottom();
  }

  _listen2events(template){
    let self = this;

    $('.follow-output', template).on('click', function(){
      self._scrollToBottom();
      self._scroll = true;
    });
  }

  _setStartedSteps(){
    let self = this;

    let new_steps = this.model._getSteps(this.model.get('steps'));
    this.model.set('steps', new_steps);

    this.model.get('steps').each(function(step){
      self._last_step = step.get('index');
      self._started_steps.push(step.get('uuid'));
    });
  }

  async render(fetch=true){
    if (fetch){
      await this.model.fetch({build_uuid: this.build_uuid});
      let repo = this.model.get('repository');
      let path = 'build-info?repo_id=' + repo.id + '&uuid=' + this.model.get(
	'uuid');
      this._setStartedSteps();
      wsconsumer.connectTo(path);
    }

    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    this._listen2events(compiled);
    let badge_class = utils.get_badge_class(kw.original_status);
    $('.build-status', compiled).removeClass().addClass(
      'build-status badge ' + badge_class);
    $('.obj-details-buttons-container', compiled).show();
    this.container = $(this.container_selector);
    this.container.html(compiled);
    if (!fetch){
      this.page._listen2events();
    }
    this.renderTerminal();
  }

  renderTerminal(){
    let el = document.getElementsByClassName('build-output')[0];
    this.term = new Terminal(el);
    let output = this.model.get('output');
    this.term.write(output);
  }

}

class BaseBuildSetView extends Backbone.View{

 _get_kw(){
   let title = this.model.escape('title');
   let body = this.model.escape('commit_body') || '<no body>';
   body = i18n(body);
   let status = this.model.get('status');
   let status_translation = i18n(status);
   let commit = this.model.get('commit').substr(0, 16);
   let date = this.model.get('commit_date');
   let branch = this.model.get('branch');
   let started = this.model.get('started');
   let finished = this.model.get('finished');
   let total_time = this.model.get('total_time');
   let buildset_details_link = '/buildset/' + this.model.get('id');
   let repo = this.model.get('repository');
   let repo_name = _.escape(repo.name);
   let number = this.model.get('number');
   let builds = this.model.get('builds');
   let author = this.model.escape('author');

   let escaped_builds = new Array();

   for (let i in builds){
     let build = builds[i];
     let escaped_build;
     try{
       escaped_build = {id: build.get('uuid'),
			name: build.escape('name'),
			status_class: ' build-' + build.status,
			status: build.status,
			details_link: '/build/' + build.get('uuid'),
			builder: {id: build.get('builder').id,
				  name: _.escape(build.get('builder').name)}};
     }catch(e){
       if (!e instanceof TypeError){
	 throw e;
       }
     }
     escaped_builds.push(escaped_build);
   }

   return {title: title, body: body, status: status_translation,
	   commit: commit, original_status: status,
	   date: date, started: started, finished: finished,
	   branch: branch, total_time: total_time,
	   repo_name: repo_name, number: number,
	   buildset_details_link: buildset_details_link,
	   builds: escaped_builds, author: author};
 }
}


class BuildInfoView extends Backbone.View{

  constructor(options){
    options = options || {'tagName': 'li'};
    options.model = options.model || new Build();
    super(options);
    let self = this;
    this.$el.addClass('builder-build-li build-info-row box-shadow');

    this.directive = {'.builder-name': 'builder_name',
		      '.build-status': 'status',
		      '.build-details-link @href': 'details_link'};

    this.template_selector = '.template .builder-build-container';
    this.container_selector = '.builds-ul';

    this.model.on({'change': function(){self.render();}});
  }

  _get_kw(){
    let uuid = this.model.get('uuid');
    let name = _.escape(this.model.get('builder').name);
    let status = this.model.get('status');
    let status_translation = i18n(status);
    let details_link = '/build/' + uuid;
    let builder = {'id': this.model.get('builder').id,
		   'name': _.escape(this.model.get('builder').name)};
    return {uuid: uuid, builder_name: name, status: status_translation,
	    original_status: status,
	    details_link: details_link, builder: builder};
  }

  render(){
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    let status_class = 'build-' + kw.original_status;

    this.$el.removeClass('build-running');
    this.$el.html('');

    this.$el.addClass(status_class);
    this.$el.append(compiled);
    return this;
  }
}

class BuildSetDetailsView extends BaseBuildSetView{

  constructor(options){
    options = options || {'tagName': 'div'};
    options.model = options.model || new BuildSet();
    super(options);
    this.buildset_id = options.buildset_id;
    this.directive = {
      '.repo-name': 'repo_name',
      '.buildset-number': 'number',
      '.commit-title': 'title',
      '.commit-branch': 'branch',
      '.commit-author': 'author',
      '.buildset-status': 'status',
      '.buildset-commit': 'commit',
      '.buildset-commit-date': 'date',
      '.buildset-started': 'started',
      '.buildset-total-time': 'total_time',
      '.buildset-commit-body': 'body',
    };
    let self = this;

    $(document).on('buildset_started buildset_finished', function(e, data){
      self.model.set(data);
      self.render();
    });

    this.template_selector = '.template #buildset-details';
    this.container_selector = '#buildset-details-container';
  }

  _connect2ws(){
    let repo_id = $('#repo-id').val();
    let path = 'buildset-info?repo_id=' + repo_id;
    wsconsumer.connectTo(path);
  }

  _setBuilds(buildset){
    utils.setBuildsForBuildSet(buildset);
  }

  async render(){
    let self = this;

    await this.model.fetch({buildset_id: this.buildset_id});
    this._setBuilds(this.model);
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    $('.wait-toxic-spinner').hide();

    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));

    let builds_container = $('.builds-ul', compiled);

    for (let i in this.model.get('builds')){
      let build = this.model.get('builds')[i];
      let build_view = new BuildInfoView({model: build});
      builds_container.append(build_view.render().$el);
    }
    let badge_class = utils.get_badge_class(kw.original_status);

    if (kw.status != 'running'){
      $('.fa-cog', compiled).hide();
    }
    $('.buildset-status', compiled).addClass(badge_class);
    $('.obj-details-buttons-container', compiled).show();
    this.container = $(this.container_selector);
    this.container.html(compiled);
    this._connect2ws();
  }

}

class BuildSetInfoView extends BaseBuildSetView{

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
      '.buildset-total-time': 'total_time',
      '.buildset-title-container a@href': 'buildset_details_link',
    };

    this.template_selector = '.template .buildset-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    let self = this;
    this.model.on({'change': function(){self.getRendered();}});
  }


  getRendered(){
    let self = this;
    let kw = this._get_kw();
    kw.total_time = kw.total_time || '<still running>';
    let compiled = $(this.compiled_template(kw));

    if (kw.started){
      $('.buildset-total-time-row', compiled).show();
    }
    let status = kw.original_status;

    $('.fa-redo', compiled).on('click', function(){
      self.rescheduleBuildSet(compiled);
    });

    if (kw.original_status != 'running'){
      $('.fa-cog', compiled).hide();
    }else{
      $('.fa-redo', compiled).hide();
    }

    let badge_class = utils.get_badge_class(status);
    compiled.addClass('repo-status-' + status.replace(' ', '-'));
    $('.badge', compiled).addClass(badge_class);
    this.$el.html(compiled);
    router.setUpLinks(this.$el);
    return this.$el;
  }

  async rescheduleBuildSet(el_container){
    utils.rescheduleBuildSet(this.model, el_container);
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
  _connect2ws(){
    let path = 'repo-buildsets?repo_name=' + this.repo_name;
    wsconsumer.connectTo(path);
  }

  async _fetch_items(){
    let self = this;
    $(document).off('build_preparing build_started build_finished');

    let kw = {data: {repo_name: this.repo_name,
		     summary: true}};
    await this.model.fetch(kw);
    this._connect2ws();
    $('.buildset-list-top-page-header-info').fadeIn(300);

    // we need to connect to the event after we fetch the data
    // otherwise will have duplicates in the list.
    this.model.on('add', function(buildset){
      self._render_obj(buildset, true);
    });
  }

  _get_view(model){
    return new BuildSetInfoView({model: model});
  }
}
