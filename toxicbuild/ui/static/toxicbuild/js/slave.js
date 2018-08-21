// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

var TOXIC_SLAVE_API_URL = window.TOXIC_API_URL + 'slave/';

class Slave extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_SLAVE_API_URL;
  }
}


class SlaveList extends BaseCollection{

  constructor(models, options){
    super(models, options);
    this.model = Slave;
    this.url = TOXIC_SLAVE_API_URL;
  }
}


class SlaveInfoView extends Backbone.View{
  // The info about a slave shown in a slave list

  constructor(options){
    options = options || {'tagName': 'div'};
    super(options);
    this.model = this.model || new Slave();

    this.directive = {
      '.slave-info-name': 'name',
      '.slave-details-link@href': 'details_link',
      '.slave-info-host': 'host',
      '.slave-info-port': 'port',
    };
    this.template_selector = '.template .slave-info';
    this.compiled_template = $p(this.template_selector).compile(
      this.directive);

  }

  _get_kw(){
    let name = this.model.escape('name');
    let host = this.model.escape('host');
    let port = this.model.escape('port');
    let details_link = '/slave/' + name;
    return {name: name, host: host, port: port, details_link: details_link};
  }

  getRendered(){
    let kw = this._get_kw();
    let compiled = $(this.compiled_template(kw));
    return compiled;
  }

}

class SlaveListView extends Backbone.View{

  constructor(){
    let model = new SlaveList();
    let options = {'tagName': 'ul',
		   'model': model};

    super(options);
    this._info_view = SlaveInfoView;
 }

  _render_slave(model){
    let view = new this._info_view({'model': model});
    let rendered = view.getRendered();
    this.$el.append(rendered.hide().fadeIn(300));
    return rendered;
  }

  _render_list(){
    $('#slave-list-container').html(this.$el);
    var self = this;
    this.model.each(function(model){self._render_slave(model);});
    return true;
  }

  async render_all(){
    await this.model.fetch();
    $('.wait-toxic-spinner').hide();
    $('.top-page-slaves-info-container').fadeIn();
    this._render_list();
  }

}
