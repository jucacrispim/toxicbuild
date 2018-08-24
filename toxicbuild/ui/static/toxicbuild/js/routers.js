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


class DashboardRouter extends Backbone.Router{

  constructor(options){
    options = options || {};

    let routes = {'': 'showMainPage',
		  'settings/repositories': 'showRepoListSettingsPage',
		  'settings/slaves': 'showSlaveListSettingsPage',
		  'repository/add': 'showRepoAddPage',
		  'slave/add': 'showSlaveAddPage',
		  'slave/:owner/:name': 'showSlaveSettingsPage',
		  ':owner/:name/settings': 'showRepoSettingsPage'};

    options['routes'] = routes;
    super(options);
    this.template_container = jQuery('#main-area-container');
    this.main_template = '/templates/main';
    this._last_url = null;
  }

  _getCurrentPath(){
    return window.location.pathname;
  }

  navigate(fragment, options){
    if (!options || !options.replace){
      this._last_url = this._getCurrentPath();
    }
    let r = super.navigate(fragment, options);
    return r;
  }

  setUpLinks(){
    let self = this;
    jQuery('a').each(function(i, el){
      jQuery(el).click(function(e){
	let a_el = jQuery(this);
	let href = a_el.attr('href');
	let noroute = a_el.data('noroute');
	let trigger = !a_el.data('notrigger');
	if (href != '#' && !noroute){
	  e.preventDefault();
	  self.navigate(href, {'trigger': trigger});
	}
      });
    });
  }

  go2lastURL(){
    let url = this._last_url || '/';
    this.redir(url);
  }

  redir(url, trigger=true, replace=false){
    this.navigate(url, {'trigger': trigger,
			'replace': replace});
  }

  async _showPage(page){
    await page.fetch_template();
    await page.render();
    this.setUpLinks();
  }

  async showMainPage(){
    let page = new MainPage({router: this});
    await this._showPage(page);
  }

  async showRepoListSettingsPage(){
    let page = new SettingsPage({router: this,
				 settings_type: 'repositories'});
    await this._showPage(page);
  }

  async showSlaveListSettingsPage(){
    let page = new SettingsPage({router: this,
				 settings_type: 'slaves'});
    await this._showPage(page);
  }

  async showRepoSettingsPage(owner, name){
    let full_name = owner + '/' + name;
    let page = new RepositoryDetailsPage(this, full_name);
    await this._showPage(page);
  }

  async showRepoAddPage(){
    let page = new RepositoryAddPage(this);
    await this._showPage(page);
  }

  async showSlaveSettingsPage(owner, name){
    let full_name = owner + '/' + name;
    let page = new SlaveDetailsPage(this, full_name);
    await this._showPage(page);
  }

  async showSlaveAddPage(){
    let page = new SlaveAddPage(this);
    await this._showPage(page);
  }

}
