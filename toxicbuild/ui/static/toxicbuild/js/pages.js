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

class BasePage extends Backbone.View{

  constructor(options){
    $(document).off(
      'buildset_started buildset_finished build_started build_finished');
    $(document).off(
      'buildset_added step_started step_finished build_preparing');

    super();
    this.router = options.router;
    this.template_container = $('#main-area-container');
  }

  async fetch_template(){
    wsconsumer.disconnect();
    let template = await $.ajax({'url': this.template_url});
    this.template_container.html(template);
  }

}

class SettingsPage extends BasePage{

  constructor(options){
    super(options);
    let self = this;
    this.right_sidebar = null;
    this.nav_pills = null;
    this.template_url = this._get_template_url(options.settings_type);
    this.main_template_url = this._get_main_template_url(options.settings_type);
    this.main_template_container = this._get_main_template_container();
    this._set_list_view(options.settings_type);
    this._already_listen = false;

    $(document).on('locale-changed', function(){
      utils.loadTranslations(STATIC_URL);
      self._reRender();
    });
  }

  async _reRender(){
    await this.fetch_template();
    await this.render();
  }

  _get_main_template_container(){
    return $('#settings-sides');
  }
  _get_template_url(settings_type){
    return '/templates/settings/' + settings_type;
  }

  _get_main_template_url(settings_type){
    return '/templates/settings/main/' + settings_type;
  }

  _set_list_view(settings_type){
    if (settings_type == 'repositories'){
      this.list_view = new RepositoryListView('enabled');
    }else if(settings_type == 'slaves'){
      this.list_view = new SlaveListView();
    }else if(settings_type == 'ui'){
      this.list_view = new UISettingsView();
    }else if(settings_type == 'user'){
      this.list_view = new UserSettingsView();
    }
  }

  _listen2events(){
    if (this._already_listen){
      return false;
    }
    let self = this;
    $('#manage-slaves-link').on('click', async function(e){
      e.preventDefault();
      await self.render_main('slaves');
    });

    $('#manage-repositories-link').on('click', async function(e){
      e.preventDefault();
      await self.render_main('repositories');
    });

    $('#manage-ui-link').on('click', async function(e){
      e.preventDefault();
      await self.render_main('ui');
    });

    $('#manage-user-link').on('click', async function(e){
      e.preventDefault();
      await self.render_main('user');
    });

    self._already_listen = true;
    return true;
  }
  async render(){
    this.right_sidebar = $('.settings-right-side');
    this.nav_pills = $('.nav-container');
    await this.list_view.render_all();
    this._listen2events();
    this.right_sidebar.fadeIn(300);
    this.nav_pills.fadeIn(300);
  }

  _handle_navigation(settings_type){
    $('#manage-slaves-link').removeClass('active box-shadow');
    $('#manage-repositories-link').removeClass('active box-shadow');
    $('#manage-ui-link').removeClass('active box-shadow');
    $('#manage-user-link').removeClass('active box-shadow');
    $('#manage-' + settings_type + '-link').addClass('active box-shadow');
  }

  _checkRenderPath(settings_type){
    let path = this.router._getCurrentPath();
    let next = '/settings/' + settings_type;
    return path != next;
  }

  async render_main(settings_type, force=false){
    if(!this._checkRenderPath(settings_type) && !force){
      return;
    }
    let href = '/settings/' + settings_type;
    this.router.navigate(href, {'trigger': false});

    this._handle_navigation(settings_type);
    this.template_url = this._get_template_url(settings_type);
    this.main_template_url = this._get_main_template_url(settings_type);
    this.main_template_container = this._get_main_template_container();
    await this.fetch_main_template();
    $('.wait-toxic-spinner').show();
    this._set_list_view(settings_type);
    await this.render();
    this.router.setUpLinks();
  }

  async fetch_main_template(){
    let template = await $.ajax({url: this.main_template_url});
    this.main_template_container.html(template);
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

class BuildSetListPage extends BasePage{

  constructor(options){
    super(options);
    this.full_name = options.full_name;
    this.template_url = '/templates/buildset-list/' + this.full_name;
    this.list_view = new BuildSetListView(this.full_name);
  }

  async render(){
    await this.list_view.render_all();
  }
}


class WaterfallPage extends BasePage{

  constructor(options){
    super(options);
    this.repo_name = options.repo_name;
    this.template_url = '/templates/waterfall/' + this.repo_name;
    this.view = new WaterfallView(this.repo_name);
  }

  async render(){
    await this.view.render();
  }

}

class BaseFloatingPage extends BasePage{

  constructor(options){
    super(options);
    this.right_sidebar = null;
    this._container = null;
    this._inner = null;
  }

  _set_last_url(reject_regex){
    let url = this.router._last_urls.pop();
    while(url && url.match(reject_regex)){
      url = this.router._last_urls.pop();
    }
    this.router._last_urls.push(url);
  }

  _listen2events(){
    let self = this;

    let close_btn = $('.details-main-container .close-btn');
    let reject_regex = /^\/build\/.*/;
    close_btn.on('click', function(e){
      self.close_page(reject_regex);
    });

    let cancel_btn = $('.buttons-container #btn-cancel-save');
    cancel_btn.on('click', function(e){
      self.close_page(reject_regex);
    });

    // so, when we render a page, we unbind from these *-using-form events
    // because only one form action can be performed at the same time.
    // close on remove
    $(document).unbind('obj-removed-using-form');
    $(document).on('obj-removed-using-form', function(e){
      self.close_page();
    });

    // redir to settings on add
    $(document).unbind('obj-added-using-form');
    $(document).on('obj-added-using-form', function(e, full_name){
      self.redir2settings(full_name);
    });


  }

  close_page(reject_regex=null){
    if (reject_regex){
      this._set_last_url(reject_regex);
    }
    this.router.go2lastURL();
  }

  redir2settings(){
    throw new Error('You must implement redir2settings()');
  }

  _getContainerInner(){
    throw new Error("You must implement _getContainerInner()");
  }

  _prepareOpenAnimation(){
    this._getContainerInner();
    this._inner.hide();
    this._container.hide();
    this._container.prop('style', 'margin:0 50% 0px 50%;min-height:0');
  }

  _animateOpen(){
    let self = this;
    this._container.show();
    this._container.animate({'margin': '-10px', 'min-height': '89vh'}, 400,
			    function(){self._inner.fadeIn(100);
				       self.right_sidebar.fadeIn(100);});
  }

}


class BaseOneSideFloatingPage extends BaseFloatingPage{

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.nav-container');
  }

  _animateOpen(){
    let self = this;
    this._container.show();
    this._container.animate({'margin': '-10px', 'min-height': '89vh'}, 400,
			    function(){self._inner.fadeIn(100);});
  }

}


class BuildDetailsPage extends BaseOneSideFloatingPage{

  constructor(options){
    super(options);
    this.build_uuid = options ? options.build_uuid : '';
    this.template_url = '/templates/build/' + this.build_uuid;
    this.view = new BuildDetailsView({build_uuid: this.build_uuid});
  }

  async render(){

    this._prepareOpenAnimation();
    await this.view.render();
    this._listen2events();
    $('.wait-toxic-spinner').hide();
    this._animateOpen();
  }
}

class BuildSetDetailsPage extends BaseOneSideFloatingPage{

  constructor(options){
    super(options);
    this.buildset_id = options ? options.buildset_id : '';
    this.template_url = '/templates/buildset/' + this.buildset_id;
    this.view = new BuildSetDetailsView({buildset_id: this.buildset_id});
  }

  async render(){

    this._prepareOpenAnimation();
    await this.view.render();
    this._listen2events();
    $('.wait-toxic-spinner').hide();
    this._animateOpen();
  }

  close_page(){
    let reject_regex = /^\/build(set|)\/.*/;
    super.close_page(reject_regex);
  }
}

class BaseRepositoryPage extends BaseFloatingPage{

  constructor(router){
    super({router: router});
    this.template_url = '/templates/repo-details';
    this.repo_details_view = null;
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

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.nav-container');
  }


  async render(){
    this.add_message_container = $('.add-repo-message-container');
    this.right_sidebar = $('.settings-right-side');

    this._prepareOpenAnimation();

    await this.repo_details_view.render_details();
    $('.repo-config-advanced-container').hide();
    this._listen2events();

    this._animateOpen();
  }

  redir2settings(full_name){
    let url = '/' + full_name + '/settings';
    this.router.redir(url, true, true);
  }

  _listen2events(){
    let self = this;
    super._listen2events();
    $(document).on('obj-added-using-form', function(e, type, full_name){
      if (type == 'repository'){
	self.redir2repo_settings(full_name);
      }else if (type == 'slave'){
	self.redir2slave_settings(full_name);
      }
    });
  }
}

class RepositoryDetailsPage extends BaseRepositoryPage{

  constructor(router, full_name){
    super(router);
    this.repo_details_view = new RepositoryDetailsView(full_name);
    this.nav_pills = null;
    this.template_url = '/templates/repo-details/' + full_name;
  }

  _toggleAdvanced(){
    let container = $(
      '.repo-config-advanced-container #repo-details-advanced-container');

    let angle_container = $(
      '.repo-config-advanced-container #advanced-angle-span');

    container.toggle(300);

    let help = $('.settings-right-side .advanced-help-container');
    if (help.is(':visible')){
      angle_container.removeClass('fa-angle-down').addClass('fa-angle-right');
      help.fadeOut(300);
    }else{
      angle_container.removeClass('fa-angle-right').addClass('fa-angle-down');
      help.fadeIn(300);
    }
  }

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.add-repo-message-container');
  }

  _listen2events(){
    let self = this;

    super._listen2events();
    $('.repo-config-advanced-span').on('click', function(e){
      self._toggleAdvanced();
    });
  }

  async render(){
    this.nav_pills = $('.nav-container');
    this.right_sidebar = $('.settings-right-side');
    this._prepareOpenAnimation();
    await this.repo_details_view.render_details();

    this._listen2events();
    this._animateOpen();
  }

  close_page(){
    let regex = /\/repository\/add$/;
    super.close_page(regex);
  }

}

class RepositoryNotificationsPage extends BaseFloatingPage{

  constructor(options){
    super(options);
    this.repo_name = options.repo_name;
    this.nav_pills = null;
    this.template_url = '/templates/repo-notifications/' + this.repo_name;
  }

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.advanced-help-container').not('.add-repo-message-container');
  }


  async render(){
    let repo_id = $('#repo-id').val();
    this.view = new NotificationListView(repo_id);
    this.nav_pills = $('.nav-container');
    this.right_sidebar = $('.settings-right-side');
    this._prepareOpenAnimation();
    await this.view.render_all();
    $('.wait-toxic-spinner').hide();
    this._listen2events();
    this._animateOpen();
  }

  close_page(){
    let regex = /\/(settings|notifications)$/;
    super.close_page(regex);
  }
}

class BaseSlaveDetailsPage extends BaseFloatingPage{

  constructor(router, name){
    super({router: router});
    this.template_url = '/templates/slave-details';
    this.name = name;
    this.view = null;
  }

  async render(){
    this.right_sidebar = $('.settings-right-side');
    this._prepareOpenAnimation();
    await this.view.render_details();
    this._listen2events();
    this._animateOpen();
  }
}

class SlaveDetailsPage extends BaseSlaveDetailsPage{

  constructor(router, name){
    super(router, name);
    this.view = new SlaveDetailsView({name: this.name});
  }

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.add-slave-message-container');
  }
}

class SlaveAddPage extends BaseSlaveDetailsPage{

  constructor(router){
    super(router);
    this.view = new SlaveAddView();
  }

  _getContainerInner(){
    this._container = $('.details-main-container');
    this._inner = $('div', this._container).not('.wait-toxic-spinner').not(
      '.nav-container');
  }

  redir2settings(full_name){
    let url = '/slave/' + full_name;
    this.router.redir(url, true, true);
  }
}
