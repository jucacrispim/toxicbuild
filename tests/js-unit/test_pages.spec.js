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
    this.page = new BasePage();
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
    this.page = new SettingsPage();
    this.page.repo_list_view.render_all = jasmine.createSpy('render-all');
  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.repo_list_view.render_all).toHaveBeenCalled();
  });
});

describe('MainPageTest', function(){

  beforeEach(function(){
    this.page = new MainPage();
    this.page.repo_list_view.render_enabled = jasmine.createSpy(
      'render-enabled');

  });

  it('test-render', async function(){
    await this.page.render();
    expect(this.page.repo_list_view.render_enabled).toHaveBeenCalled();
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

  it('test-close-page', function(){
    spyOn(this.page.router, 'go2lastURL');
    this.page.close_page();
    expect(this.page.router.go2lastURL).toHaveBeenCalled();
  });

});
