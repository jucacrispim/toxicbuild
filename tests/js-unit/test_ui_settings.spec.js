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

describe('UISettingsViewTest', function(){

  beforeEach(function(){
    this.view = new UISettingsView();
  });

  it('test-hasThemeCookie', function(){
    spyOn(Cookies, 'get');
    this.view._hasThemeCookie();
    expect(Cookies.get).toHaveBeenCalled();
  });

  it('test-setThemeCookie-enabled', function(){
    spyOn(Cookies, 'set');
    this.view.setThemeCookie(true);
    expect(Cookies.set).toHaveBeenCalled();
  });

  it('test-setThemeCookie-not-enabled', function(){
    spyOn(Cookies, 'remove');
    this.view.setThemeCookie(false);
    expect(Cookies.remove).toHaveBeenCalled();
  });

  it('test-setCheckbox-has-theme', function(){
    spyOn(this.view, '_hasThemeCookie').and.returnValue(true);
    let check_el = jasmine.createSpy();
    check_el.prop = jasmine.createSpy();
    this.view._setCheckbox(check_el);
    expect(check_el.prop).toHaveBeenCalled();
  });

  it('test-setCheckbox-no-theme', function(){
    spyOn(this.view, '_hasThemeCookie').and.returnValue(false);
    let check_el = jasmine.createSpy();
    check_el.prop = jasmine.createSpy();
    this.view._setCheckbox(check_el);
    expect(check_el.prop).not.toHaveBeenCalled();
  });

  it('test-setLocaleCookie', function(){
    spyOn(Cookies, 'set');
    this.view.setLocaleCookie();
    expect(Cookies.set).toHaveBeenCalled();
  });

});
