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


class BuildSet extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_SLAVE_API_URL;
  }
}

class BuildSetList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = BuildSet;
    this.url = TOXIC_BUILDSET_API_URL;
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
    compiled.addClass('repo-status-' + status);
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
