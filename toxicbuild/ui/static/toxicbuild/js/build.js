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
    let builds  = this.attributes ? this.attributes.builds : [];
    let self = this;
    if (options && !options.no_events){
      $(document).on('build_started build_finished', function(e, data){
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
    super(attributes, options);
    this._api_url = TOXIC_BUILD_API_URL;
    let steps = attributes && attributes.steps ? attributes.steps : [];
    this.set('steps', this._getSteps(steps));
  }

  _getSteps(steps){
    let build_steps = new Array();
    for (let i in steps){
      let step = steps[i];
      let build_step = new BuildStep(step);
      build_steps.push(build_step);
    }
    let steps_list = new BuildStepList();
    steps_list.reset(steps);
    return steps_list;
  }

}

class BuildStep extends BaseModel{

  constructor(attributes, options){
    options = options || {};
    options.idAttribute = 'uuid';
    super(attributes, options);
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
    buildset.set(data);
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
		      '.build-number': 'build_number',
		      '.commit-author': 'commit_author',
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
    let build_number = this.model.get('number');
    let commit_author = this.model.escape('commit_author');
    return {command: command, status: status, output: output,
	    started: started, total_time: total_time,
	    build_number: build_number,
	    repo_name: repo_name, builder_name: builder_name,
	    commit_title: commit_title, commit_branch: commit_branch,
	    commit_author: commit_author};
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

class BaseBuildSetView extends Backbone.View{

 _get_kw(){
   let title = this.model.escape('title');
   let body = this.model.escape('body') || '<no body>';
   let status = this.model.get('status');
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

   return {title: title, body: body, status: status, commit: commit,
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
    let details_link = '/build/' + uuid;
    let builder = {'id': this.model.get('builder').id,
		   'name': _.escape(this.model.get('builder').name)};
    return {uuid: uuid, builder_name: name, status: status,
	    details_link: details_link, builder: builder};
  }

  render(){
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    let status_class = 'build-' + kw.status;

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
    let badge_class = utils.get_badge_class(kw.status);

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
    let status = kw.status;


    $('.fa-redo', compiled).on('click', function(){
      self.rescheduleBuildSet(compiled);
    });

    if (kw.status != 'running'){
      $('.fa-cog', compiled).hide();
    }else{
      $('.fa-redo', compiled).hide();
    }

    let badge_class = utils.get_badge_class(status);
    compiled.addClass('repo-status-' + status.replace(' ', '-'));
    $('.badge', compiled).addClass(badge_class);
    this.$el.html(compiled);
    return this.$el;
  }

  async rescheduleBuildSet(el_container){
    let repo = new Repository({'id': this.model.get('repository').id});
    let branch = this.model.get('branch');
    let named_tree = this.model.get('commit');

    let spinner = $('.spinner-reschedule-buildset', el_container);
    let retry_btn = $('.fa-redo', el_container);
    retry_btn.hide();
    spinner.show();
    try{
      await repo.start_build(branch, null, named_tree);
      utils.showSuccessMessage('Buildset re-scheduled');
    }catch(e){
      utils.showErrorMessage('Error re-scheduling buildset');
    }
    retry_btn.show();
    spinner.hide();
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
    let self = this;
    this._connect2ws();
  }

  _connect2ws(){
    let path = 'repo-buildsets?repo_name=' + this.repo_name;
    wsconsumer.connectTo(path);
  }

  async _fetch_items(){
    let self = this;

    let kw = {data: {repo_name: this.repo_name,
		     summary: true}};
    await this.model.fetch(kw);
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
