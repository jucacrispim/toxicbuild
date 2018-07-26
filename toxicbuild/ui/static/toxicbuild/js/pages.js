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

  constructor(router){
    super();
    this.router = router;
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

class RepositoryDetailsPage extends BasePage{

  constructor(router, full_name){
    super(router);
    this.template_url = '/templates/repo-details';
    this.repo_details_view = new RepositoryDetailsView(full_name);
    this.right_sidebar = null;
    this.nav_pills = null;
  }

  _toggleAdvanced(){
    let container = jQuery(
      '.repo-config-advanced-container #repo-details-advanced-container');

    let angle_container = jQuery(
      '.repo-config-advanced-container #advanced-angle-span');

    container.toggle(300);

    let help = jQuery('.settings-right-side .advanced-help-container');
    if (help.is(':visible')){
      angle_container.removeClass('fa-angle-down').addClass('fa-angle-right');
      help.fadeOut(300);
    }else{
      angle_container.removeClass('fa-angle-right').addClass('fa-angle-down');
      help.fadeIn(300);
    }
  }

  _listen2events(){
    let self = this;
    jQuery('.repo-config-advanced-span').on('click', function(e){
      self._toggleAdvanced();
    });

    let close_btn = jQuery('.repo-details-main-container .close-btn');
    close_btn.on('click', function(e){
      self.close_page();
    });

    let cancel_btn = jQuery(
      '.repo-details-buttons-container #btn-cancel-save-repo');
    cancel_btn.on('click', function(e){
      self.close_page();
    });
  }

  async render(){
    this.nav_pills = jQuery('.nav-container');
    this.right_sidebar = jQuery('.settings-right-side');
    await this.repo_details_view.render_details();
    this.right_sidebar.fadeIn(300);
    this.nav_pills.fadeIn(300);
    this._listen2events();
  }

  close_page(){
    this.router.go2lastURL();
  }
}
