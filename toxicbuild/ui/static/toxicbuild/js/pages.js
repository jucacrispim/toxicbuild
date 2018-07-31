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

class BaseRepositoryPage extends BasePage{

  constructor(router){
    super(router);
    this.template_url = '/templates/repo-details';
    this.repo_details_view = null;
    this.right_sidebar = null;
  }

  _listen2events(){
    let self = this;

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

  close_page(){
    this.router.go2lastURL();
  }

  _getContainerInner(){
    this._container = jQuery('.repo-details-main-container');
    this._inner = jQuery('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.nav-container');
  }

  _prepareOpenAnimation(){
    this._inner.hide();
    this._container.prop('style', 'margin:0 50% 0px 50%;min-height:0');
  }

  _animateOpen(){
    let self = this;

    this._container.animate({'margin': '-10px', 'min-height': '89vh'}, 400,
			    function(){self._inner.fadeIn(100);
				       self.right_sidebar.fadeIn(100);});
  }

}

class RepositoryAddPage extends BaseRepositoryPage{

  constructor(router){
    super(router);
    this.repo_details_view = new RepositoryAddView();
    this.add_message_container = null;

    this._container = null;
    this._inner = null;
  }

  async render(){
    this._getContainerInner();
    this.add_message_container = jQuery('.add-repo-message-container');
    this.right_sidebar = jQuery('.settings-right-side');

    this._prepareOpenAnimation();

    await this.repo_details_view.render_details();
    jQuery('.repo-config-advanced-container').hide();
    this._listen2events();

    this._animateOpen();
  }

  redir2repo_settings(full_name){
    let url = '/' + full_name + '/settings';
    this.router.redir(url, true, true);
  }

  _listen2events(){
    let self = this;
    super._listen2events();
    jQuery(document).on('repo-added', function(e, full_name){
      self.redir2repo_settings(full_name);
    });
  }
}

class RepositoryDetailsPage extends BaseRepositoryPage{

  constructor(router, full_name){
    super(router);
    this.repo_details_view = new RepositoryDetailsView(full_name);
    this.nav_pills = null;
  }

  _getContainerInner(){
    this._container = jQuery('.repo-details-main-container');
    this._inner = jQuery('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.add-repo-message-container');
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

    super._listen2events();
    jQuery('.repo-config-advanced-span').on('click', function(e){
      self._toggleAdvanced();
    });

    // close on remove
    jQuery(document).on('repo-removed', function(e){
      e.stopImmediatePropagation();
      self.close_page();
    });
  }

  async render(){
    this.nav_pills = jQuery('.nav-container');
    this.right_sidebar = jQuery('.settings-right-side');
    this._getContainerInner();
    this._prepareOpenAnimation();
    await this.repo_details_view.render_details();

    this._listen2events();
    this._animateOpen();
  }

}
