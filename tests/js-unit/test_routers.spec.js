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

describe('DashboarRouterTest', function(){

  beforeEach(function(){
    this.router = new DashboardRouter();
    this.first_a = jQuery('a', affix('.first a'));
    this.first_a.attr('href', '#');
    this.second_a = jQuery('a', affix('.second a'));
    this.second_a.data('noroute',true);
    this.third_a = jQuery('a', affix('.third a'));
    this.third_a.attr('href', '/some/where');
  });

  it('test-setup-links', function(){
    spyOn(this.router, 'navigate');
    this.router.setUpLinks();
    this.first_a.click();
    this.second_a.click();
    this.third_a.click();
    expect(this.router.navigate.calls.allArgs().length).toEqual(1);
  });

  it('test-showPage', async function(){
    let page = jasmine.createSpy('test-page');
    page.fetch_template = jasmine.createSpy('fetch_template');
    page.render = jasmine.createSpy('render');
    await this.router._showPage(page);
    expect(page.fetch_template).toHaveBeenCalled();
    expect(page.render).toHaveBeenCalled();
  });

  it('test-showMainPage', async function(){
    this.router._showPage = jasmine.createSpy('_showPage');
    await this.router.showMainPage();
    let page = this.router._showPage.calls.allArgs()[0][0];
    expect((page instanceof MainPage)).toBe(true);
  });

  it('test-showRepoListSettingsPage', async function(){
    this.router._showPage = jasmine.createSpy('_showPage');
    await this.router.showRepoListSettingsPage();
    let page = this.router._showPage.calls.allArgs()[0][0];
    expect((page instanceof SettingsPage)).toBe(true);
    expect((page.list_view instanceof RepositoryListView)).toBe(true);
  });

  it('test-showSlaveListSettingsPage', async function(){
    this.router._showPage = jasmine.createSpy('_showPage');
    await this.router.showSlaveListSettingsPage();
    let page = this.router._showPage.calls.allArgs()[0][0];
    expect((page instanceof SettingsPage)).toBe(true);
    expect((page.list_view instanceof SlaveListView)).toBe(true);
  });

  it('test-showRepoSettingsPage', async function(){
    this.router._showPage = jasmine.createSpy('_showPage');
    await this.router.showRepoSettingsPage();
    let page = this.router._showPage.calls.allArgs()[0][0];
    expect((page instanceof RepositoryDetailsPage)).toBe(true);
  });

  it('test-showRepoAddPage', async function(){
    this.router._showPage = jasmine.createSpy('_showPage');
    await this.router.showRepoAddPage();
    let page = this.router._showPage.calls.allArgs()[0][0];
    expect((page instanceof RepositoryAddPage)).toBe(true);
  });

  it('test-go2lastURL', function(){
    spyOn(this.router, 'redir');
    this.router._last_urls = ['/some/thing'];
    this.router.go2lastURL();
    expect(this.router.redir).toHaveBeenCalled();
  });

  it('test-redir', function(){
    spyOn(this.router, 'navigate');
    this.router.redir('full/name');
    expect(this.router.navigate).toHaveBeenCalled();
  });

  it('test-navigate-replace', function(){
    this.router.navigate('/bla/ble', {'replace': true});
    expect(this.router._last_urls.length).toEqual(0);
  });

  it('test-navigate-dont-replace', function(){
    spyOn(this.router, '_getCurrentPath').and.returnValue('/bla/bli');
    this.router.navigate('/bla/ble');
    expect(this.router._last_urls.length).toEqual(1);
  });

});
