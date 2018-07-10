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

var TOXIC_REPO_API_URL = window.TOXIC_API_URL + 'repo/';

class Repository extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this.url = TOXIC_REPO_API_URL;
  }

  async _post2api(url, body){
    let resp = await jQuery.ajax({'url': url, 'data': body, 'type': 'post'});
    return jQuery.parseJSON(resp);
  }

  async add_slave(slave){
    let url = this.get('url') + 'add-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async remove_slave(slave){
    let url = this.get('url') + 'remove-slave?' + 'id=' + this.id;
    let body = {'id': slave.id};
    return this._post2api(url, body);
  }

  async add_branch(branches_config){
    let url = this.get('url') + 'add-branch?id=' + this.id;
    let body = {'add_branches': branches_config};
    return this._post2api(url, body);
  }

  async remove_branch(branches){
    let url = this.get('url') + 'remove-branch?id=' + this.id;
    let body = {'remove_branches': branches};
    return this._post2api(url, body);
  }

  async enable_plugin(plugin_config){
    let url = this.get('url') + 'enable-plugin?id=' + this.id;
    return this._post2api(url, plugin_config);
  }

  async disable_plugin(plugin_name){
    let url = this.get('url') + 'disable-plugin?id=' + this.id;
    let body = {'plugin_name': plugin_name};
    return this._post2api(url, body);
  }

  async start_build(branch, builder_name=null, named_tree=null,
		    slaves=null, builders_origin=null){
    let url = this.get('url') + 'start-build?id=' + this.id;
    let body = {'branch': branch, 'builder_name': builder_name,
		'named_tree': named_tree, 'slaves': slaves,
		'builders_origin': builders_origin};
    return this._post2api(url, body);

  }

  async cancel_build(build_uuid){
    let url = this.get('url') + 'cancel-build?id=' + this.id;
    let body = {'build_uuid': build_uuid};
    return this._post2api(url, body);
  }

}


class RepositoryList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Repository;
    this.url = TOXIC_REPO_API_URL;
  }

}


class RepositoryInfoView extends Backbone.View{
  // A view to display the repository information in the
  // repository list

  initialize(){
    this.directive = {'.repository-info-name': 'name',
		      '.repository-info-status': 'status',
		      '.buildset-commit': 'commit',
		      '.buildset-title': 'title',
		      '.buildset-total-time': 'total_time',
		      '.buildset-started': 'started',
		      '.buildset-commit-date': 'commit_date'};
    this.template_selector = '.template .repository-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);
  }

  _get_kw(){
    let status = this.model.get('status');
    let last_buildset = this.model.get('last_buildset');
    let commit = last_buildset.commit ? last_buildset.commit.slice(0, 8) : '';

    let kw = {'name': this.model.get('name'),
	      'status': status, 'commit': commit,
	      'title': last_buildset.title,
	      'total_time': last_buildset.total_time,
	      'started': last_buildset.started,
	      'commit_date': last_buildset.commit_date};

    return kw;
  }

  _get_badge_class(status){
    let badge_classes = {'ready': 'secondary',
			 'running': 'primary',
			 'exception': 'exception',
			 'clone-exception': 'exception'};
    let badge_class = 'badge-' + badge_classes[status];
    return badge_class;
  }

  render(){
    let kw = this._get_kw();
    let status = kw['status'];
    let badge_class = this._get_badge_class(status);

    let compiled = jQuery(this.compiled_template(kw));
    compiled.addClass('repo-status-' + status);
    jQuery('.badge', compiled).addClass(badge_class);

    if (status == 'ready'){
      jQuery('.no-builds-info', compiled).show();
    }
    else{
      jQuery('.repository-info-last-buildset', compiled).show();
    }
    return compiled;
  }
}


class RepositoryListView extends Backbone.View{

  constructor(){
    let model = new RepositoryList();
    let options = {'tagName': 'ul',
		   'model': model};
    super(options);
  }

  initialize(){
    _.bindAll(this, 'render');
    var self = this;
    this.model.bind('sync', function(){self._render_list_if_needed();});
  }

  _render_repo(model){
    let view = new RepositoryInfoView({'model': model});
    let rendered = view.render();
    this.$el.append(rendered.hide().fadeIn(300));
    return rendered;
  }

  _render_list_if_needed(){
    // Renders the repository list if there are some repositories. If not
    // displays the welcome message
    jQuery('.wait-toxic-spinner').hide();
    if (this.model.length == 0){
      jQuery('#no-repos-info').fadeIn(300);
      return false;
    }

    jQuery('.enabled-repositories-info-container').show();
    jQuery('#repo-list-container').append(this.$el);
    var self = this;
    this.model.each(function(model){self._render_repo(model);});
    return true;
  }

  render(){
    // will trigger _render_list_if_needed
    this.model.fetch();
  }
}
