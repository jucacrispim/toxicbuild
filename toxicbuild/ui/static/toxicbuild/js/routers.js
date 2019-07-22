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


class DashboardRouter extends Backbone.Router{

  constructor(options){
    options = options || {};

    let routes = {'': 'showMainPage',
		  'settings/repositories': 'showRepoListSettingsPage',
		  'settings/slaves': 'showSlaveListSettingsPage',
		  'settings/ui': 'showUISettingsPage',
		  'settings/user': 'showUserSettingsPage',
		  'repository/add': 'showRepoAddPage',
		  'slave/add': 'showSlaveAddPage',
		  'slave/:owner/:name': 'showSlaveSettingsPage',
		  ':owner/:name/settings': 'showRepoSettingsPage',
		  ':owner/:name/notifications': 'showRepoNotificationsPage',
		  ':owner/:name/waterfall': 'showWaterfallPage',
		  ':owner/:name/': 'showBuildSetListPage',
		  'build/:build_uuid': 'showBuildDetaisPage',
		  'buildset/:buildset_id': 'showBuildSetDetaisPage'};

    options['routes'] = routes;
    super(options);
    this.template_container = jQuery('#main-area-container');
    this.main_template = '/templates/main';
    this._last_urls = new Array();
    this._loading_template = false;
    this._load_bar_size = 0;

    var nano_options = {
      classname: 'toxic-load-bar',
      id: 'top-page-loadbar',
      target: document.getElementById('top-page-loadbar')
    };

    this._load_bar = new Nanobar(nano_options);
  }

  _getCurrentPath(){
    return window.location.pathname;
  }

  navigate(fragment, options){
    if (!options || !options.replace){
      this._last_urls.push(this._getCurrentPath());
    }
    let r = super.navigate(fragment, options);
    return r;
  }

  setUpLinks(container){
    let self = this;
    let el_list;
    if (container){
      el_list = $('a', container);
    }else{
      el_list = $('a');
    }
    el_list.each(function(i, el){
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
    let url = this._last_urls.pop() || '/';
    this.redir(url);
  }

  redir(url, trigger=true, replace=false){
    this.navigate(url, {'trigger': trigger,
			'replace': replace});
  }

  async _loadTemplate(page){
    let self = this;
    self._loading_template = true;
    let p = page.fetch_template();
    p.then(function(){self._loading_template = false;});

    let load_steps = [500, 1000, 2000];
    let i = 0;
    this._load_bar.go(10);
    while (self._loading_template){
      await utils.sleep(load_steps[i]);
      i += 1;
      this._load_bar_size += 30;
      if (this._load_bar_size <= 90){
	this._load_bar.go(this._load_bar_size);
      }
    }
    this._load_bar.go(100);
    this._load_bar_size = 0;
  }

  async _showPage(page){
    // await page.fetch_template();
    await this._loadTemplate(page);
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

  async showUISettingsPage(){
    let page = new SettingsPage({router: this,
				 settings_type: 'ui'});
    await this._showPage(page);
  }

  async showUserSettingsPage(){
    let page = new SettingsPage({router: this,
				 settings_type: 'user'});
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

  async showBuildSetListPage(owner, name){
    let full_name = owner + '/' + name;
    let page = new BuildSetListPage({router: this,
				     full_name: full_name});
    await this._showPage(page);
  }

  async showWaterfallPage(owner, name){
    let full_name = owner + '/' + name;
    let page = new WaterfallPage({router: this,
				  repo_name: full_name});
    await this._showPage(page);
  }

  async showBuildDetaisPage(build_uuid){
    let page = new BuildDetailsPage({router: this,
				     build_uuid: build_uuid});
    await this._showPage(page);
  }

  async showBuildSetDetaisPage(buildset_id){
    let page = new BuildSetDetailsPage({router: this,
					buildset_id: buildset_id});
    await this._showPage(page);
  }

  async showRepoNotificationsPage(owner,name){
    let full_name = owner + '/' + name;
    let page = new RepositoryNotificationsPage({router: this,
						repo_name: full_name});
    await this._showPage(page);
  }

}
