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

describe('BasePageTest', function(){

  beforeEach(function(){
    spyOn(jQuery, 'ajax');
    affix('#main-area-container');
    this.page = new BasePage({router: jasmine.createSpy('router')});
    this.page.template_container.html = jasmine.createSpy('html_call');
  });

  it('test-fetch-template', async function(){
    await this.page.fetch_template();
    expect(this.page.template_container.html).toHaveBeenCalled();
  });
});


describe('SettingsPageTest', function(){

  beforeEach(function(){
    affix('.settings-right-side');
    affix('.nav-container');
    affix('#settings-sides');
    spyOn($, 'ajax');
    spyOn($.fn, 'html');
  });

  it('test-render-repo', async function(){
    this.page = new SettingsPage({settings_type: 'repositories'});
    this.page.list_view.render_all = jasmine.createSpy('render-all');
    await this.page.render();
    let isinstance = this.page.list_view instanceof RepositoryListView;
    expect(isinstance).toBe(true);
    expect(this.page.list_view.render_all).toHaveBeenCalled();
  });

  it('test-render-slave', async function(){
    this.page = new SettingsPage({settings_type: 'slaves'});
    this.page.list_view.render_all = jasmine.createSpy('render-all');
    await this.page.render();
    let isinstance = this.page.list_view instanceof SlaveListView;
    expect(isinstance).toBe(true);
    expect(this.page.list_view.render_all).toHaveBeenCalled();
  });

  it('test-fetch-main-template', async function(){
    let router = jasmine.createSpy('router');
    router.setUpLinks = jasmine.createSpy('setUpLinks');
    this.page = new SettingsPage({settings_type: 'slaves',
				  router: router});
    await this.page.fetch_main_template();
    expect(this.page.main_template_container.html).toHaveBeenCalled();
  });

  it('test-checkRenderPath', function(){
    let router = jasmine.createSpy('router');
    router._getCurrentPath = jasmine.createSpy('path').and.returnValue(
      '/settings/slaves');
    this.page = new SettingsPage({settings_type: 'slaves',
				  router: router});
    let r = this.page._checkRenderPath('repositories');
    expect(r).toBe(true);
  });

  it('test-render_main', async function(){
    let router = jasmine.createSpy('router');
    router.setUpLinks = jasmine.createSpy('setUpLinks');
    router._getCurrentPath = jasmine.createSpy('path').and.returnValue(
      '/settings/slaves');
    router.navigate = jasmine.createSpy('navigate');
    this.page = new SettingsPage({settings_type: 'slaves',
				  router: router});
    spyOn(this.page, 'fetch_main_template');
    spyOn(this.page, 'render');
    await this.page.render_main('repositories');
    expect(this.page.template_url).toEqual('/templates/settings/repositories');
  });

  it('test-render_main-same-page', async function(){
    let router = jasmine.createSpy('router');
    router.setUpLinks = jasmine.createSpy('setUpLinks');
    router._getCurrentPath = jasmine.createSpy('path').and.returnValue(
      '/settings/slaves');
    this.page = new SettingsPage({settings_type: 'slaves',
				  router: router});
    spyOn(this.page, 'fetch_main_template');
    spyOn(this.page, 'render');
    await this.page.render_main('slaves');
    expect(this.page.template_url).toEqual('/templates/settings/slaves');
  });

});

describe('MainPageTest', function(){

  beforeEach(function(){
    this.page = new MainPage({router: jasmine.createSpy('router')});
    this.page.repo_list_view.render_enabled = jasmine.createSpy(
      'render-enabled');
  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.repo_list_view.render_enabled).toHaveBeenCalled();
  });
});

describe('BuildSetListPageTest', function(){

  beforeEach(function(){
    this.page = new BuildSetListPage({router: jasmine.createSpy('router')});
    this.page.list_view.render_all = jasmine.createSpy('render-all');
  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.list_view.render_all).toHaveBeenCalled();
  });
});

describe('WaterfallPageTest', function(){

  beforeEach(function(){
    this.page = new WaterfallPage({router: jasmine.createSpy('router'),
				       repo_name: 'some/repo'});
    this.page.view.render = jasmine.createSpy('render-all');
  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.view.render).toHaveBeenCalled();
  });
});

describe('BaseFloatingPageTest', function(){

  beforeEach(function(){
    let router = new DashboardRouter();
    this.page = new BaseFloatingPage({router: router});
  });

  it('test-close-page', function(){
    spyOn(this.page.router, 'go2lastURL');
    this.page.close_page();
    expect(this.page.router.go2lastURL).toHaveBeenCalled();
  });

  it('test-prepareOpenAnimation', function(){
    this.page._getContainerInner = jasmine.createSpy('_getcontainerinner');
    this.page._inner = jasmine.createSpy('_inner');
    this.page._inner.hide = jasmine.createSpy('hide');
    this.page._container = jasmine.createSpy('_container');
    this.page._container.prop = jasmine.createSpy('prop');
    this.page._prepareOpenAnimation();
    expect(this.page._inner.hide).toHaveBeenCalled();
    expect(this.page._container.prop).toHaveBeenCalled();
  });

  it('test-animateOpen', function(){
    this.page._container = jasmine.createSpy('_container');
    this.page._container.animate = jasmine.createSpy('animate');
    this.page._animateOpen();
    expect(this.page._container.animate).toHaveBeenCalled();
  });

  it('test_getContainerInner', function(){
    let self = this;
    expect(function(){self.page._getContainerInner();}).toThrow(
      new Error('You must implement _getContainerInner()'));
  });

  it('test-redir2settings', function(){
    let self = this;
    expect(function(){self.page.redir2settings();}).toThrow(
      new Error('You must implement redir2settings()'));
  });
});

describe('BaseRepositoryPageTest', function(){

});

describe('RepositoryAddPageTest', function(){

  beforeEach(function(){
    let right_sidebar = affix('.settings-right-side');
    let message = affix('.add-repo-message-container');
    message.hide();
    right_sidebar.hide();
    let router = new DashboardRouter();
    this.page = new RepositoryAddPage(router);
    spyOn(this.page.repo_details_view, 'render_details');
  });

  it('test-render', async function(){
    spyOn(this.page, '_prepareOpenAnimation');
    spyOn(this.page, '_animateOpen');
    await this.page.render();
    let advanced_container = jQuery('.repo-config-advanced-container');
    let message = jQuery('.add-repo-message-container');

    expect(this.page._prepareOpenAnimation).toHaveBeenCalled();
    expect(this.page._animateOpen).toHaveBeenCalled();
  });

  it('test-redir2settings', function(){
    let full_name = 'ze/repo';
    this.page.router.redir = jasmine.createSpy('redir');
    let expected = '/ze/repo/settings';
    this.page.redir2settings(full_name);
    let called = this.page.router.redir.calls.allArgs()[0][0];
    expect(called).toEqual(expected);
  });
});

describe('RepositoryDetailsPageTest', function(){

  beforeEach(function(){
    affix('.template #repo-details-container');
    let router = new DashboardRouter();
    this.page = new RepositoryDetailsPage(router);
    this.page.repo_details_view.render_details = jasmine.createSpy(
      'render-details');
  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.repo_details_view.render_details).toHaveBeenCalled();
  });

  it('test-toogle-advanced-show', function(){
    affix('.repo-config-advanced-container #repo-details-advanced-container');
    let angle = affix('.repo-config-advanced-container #advanced-angle-span');
    let help = affix('.settings-right-side .advanced-help-container');

    spyOn(jQuery.fn, 'fadeIn');

    help.hide();
    this.page._toggleAdvanced();
    expect(jQuery.fn.fadeIn).toHaveBeenCalled();
    expect(angle.hasClass('fa-angle-down'));
  });

  it('test-toogle-advanced-hide', function(){
    affix('.repo-config-advanced-container #repo-details-advanced-container');
    let angle = affix('.repo-config-advanced-container #advanced-angle-span');
    let help = affix('.settings-right-side .advanced-help-container');

    spyOn(jQuery.fn, 'fadeOut');

    help.show();
    this.page._toggleAdvanced();
    expect(jQuery.fn.fadeOut).toHaveBeenCalled();
    expect(angle.hasClass('fa-angle-right'));
  });
});


describe('BaseSlaveDetailsPageTest', function(){

  beforeEach(function(){
    let router = new DashboardRouter();
    this.page = new BaseSlaveDetailsPage(router, 'name');
    this.page.view = new BaseSlaveDetailsView();
  });

  it('test-render', async function(){
    spyOn(this.page, '_prepareOpenAnimation');
    spyOn(this.page, '_listen2events');
    spyOn(this.page, '_animateOpen');
    spyOn(this.page.view, 'render_details');

    await this.page.render();

    expect(this.page._prepareOpenAnimation).toHaveBeenCalled();
    expect(this.page._listen2events).toHaveBeenCalled();
    expect(this.page._animateOpen).toHaveBeenCalled();
    expect(this.page.view.render_details).toHaveBeenCalled();
  });
});


describe('SlaveAddPageTest', function(){

  beforeEach(function(){
    let router = new DashboardRouter();
    this.page = new SlaveAddPage(router);
  });

  it('test-redir2settings', function(){
    let full_name = 'ze/someslave';
    this.page.router.redir = jasmine.createSpy('redir');
    let expected = '/slave/ze/someslave';
    this.page.redir2settings(full_name);
    let called = this.page.router.redir.calls.allArgs()[0][0];
    expect(called).toEqual(expected);
  });

});
