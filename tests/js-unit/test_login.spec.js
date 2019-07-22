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

describe('LoginTest', function(){
  beforeEach(function(){
    let btn_login = affix('#btn-login');
    let btn_spinner = btn_login.affix('#login-btn-spinner');
    let btn_text = btn_login.affix('#login-btn-text');
    affix('#form-signin');
    affix('#login-error-msg-container');
    affix('#inputUsername');
    affix('#inputPassword');
  });

  it('test-disable-button', function(){
    _disable_button();
    let btn_login = jQuery('#btn-login');
    expect(btn_login.hasClass('disabled')).toBe(true);
  });

  it('test-enable-button', function(){
    _enable_button();
    let btn_login = jQuery('#btn-login');
    expect(btn_login.hasClass('disabled')).toBe(false);
  });

  it('test-doLogin-invalid-form', async function(){
    spyOn(jQuery.fn, 'valid');
    jQuery.fn.valid.and.returnValue(false);
    let r = await doLogin();
    expect(r).toBe(false);
  });

  it('test-doLogin-invalid-credentials', async function(){
    spyOn(jQuery.fn, 'valid');
    jQuery.fn.valid.and.returnValue(true);
    spyOn(jQuery, 'ajax').and.throwError();
    let _location = jasmine.createSpy('location');
    _location.replace = jasmine.createSpy('replace');
    let r = await doLogin(_location);
    expect(r).toBe(false);
  });

  it('test-doLogin-ok', async function(){
    spyOn(jQuery.fn, 'valid');
    jQuery.fn.valid.and.returnValue(true);
    let _location = jasmine.createSpy('location');
    _location.replace = jasmine.createSpy('replace');
    let r = await doLogin(_location);
    expect(r).toBe(true);
  });

});
