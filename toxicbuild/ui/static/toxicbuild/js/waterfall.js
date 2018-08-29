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


class WaterfallBuilderView extends Backbone.View{

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
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    $('.builder-name', compiled).addClass(
      'builder-' + kw.status);
    return compiled;
  }
}

class WaterfallBuildView extends Backbone.View{

  constructor(options){
    super(options);
    this.build = options.build;
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

  async render(){
    await this.model.fetch();
    let header = this._renderHeader();
    let header_container = $('#waterfall-header');
    header_container.append(header);
    $('.wait-toxic-spinner').hide();
    $('#waterfall-container').fadeIn(300);
  }
}
