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

class BasePage extends Backbone.View{

  constructor(options){
    super(options);
    this.template_container = jQuery('#main-area-container');
  }

  async fetch_template(){
    let template = await jQuery.ajax({'url': this.template_url});
    this.template_container.html(template);
  }

}

class SettingsPage extends BasePage{

  constructor(options){
    super(options);
    this.right_sidebar = null;
    this.nav_pills = null;
    this.template_url = '/templates/settings';
    this.repo_list_view = new RepositoryListView('enabled');
  }

  async render(){
    this.right_sidebar = jQuery('.settings-right-side');
    this.nav_pills = jQuery('.nav-container');
    await this.repo_list_view.render_all();
    this.right_sidebar.fadeIn(300);
    this.nav_pills.fadeIn(300);
  }

}

class MainPage extends BasePage{

  constructor(options){
    super(options);
    this.template_url = '/templates/main';
    this.repo_list_view = new RepositoryListView('short');
  }

  async render(){
    await this.repo_list_view.render_enabled();
  }
}
