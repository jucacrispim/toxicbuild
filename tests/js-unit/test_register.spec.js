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

describe('RegisterHandlerTest', function(){

  beforeEach(function(){
    spyOn($, 'ajax');
    affix('#username');
    affix('#email');
    affix('#password');
    affix('#btn-register');
    this.handler = new RegisterHandler();
  });

  it('test-isAvailable', async function(){
    $.ajax.and.returnValue({'check-exists': true});
    let r = await this.handler._isAvailable('username');
    expect(r).toBe(false);
					 });

  it('test-checkAvailable-not-available', async function(){
    spyOn(this.handler, '_isAvailable').and.returnValue(false);
    await this.handler.checkAvailable('username');
    expect(this.handler._valid['username']).toBe(false);
  });

  it('test-checkAvailable-available', async function(){
    spyOn(this.handler, '_isAvailable').and.returnValue(true);
    await this.handler.checkAvailable('email');
    expect(this.handler._valid['email']).toBe(true);
  });

  it('test-is_valid-not-valid', function(){
    let valid = this.handler.is_valid();
    expect(valid).toBe(false);
  });

  it('test-is_valid-ok', function(){
    this.handler._valid = {'username': true, 'email': true,
			   'password': true};
    let valid = this.handler.is_valid();
    expect(valid).toBe(true);
  });

  it('test-handleButton-not-ok', function(){
    spyOn(this.handler, 'is_valid').and.returnValue(false);
    this.handler.handleButton();
    let btn = $('#btn-register');
    expect(btn.prop('disabled')).toBe(true);
  });

  it('test-handleButton-ok', function(){
    spyOn(this.handler, 'is_valid').and.returnValue(true);
    this.handler.handleButton();
    let btn = $('#btn-register');
    expect(btn.prop('disabled')).toBe(false);
  });

  it('test-register-ok', async function(){
    spyOn(this.handler, '_redir');
    await this.handler.register();
    expect(this.handler._redir).toHaveBeenCalled();
  });

  it('test-register-error', async function(){
    spyOn(utils, 'showErrorMessage');
    $.ajax.and.throwError();
    await this.handler.register();
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-validateName', async function(){
    spyOn(this.handler, 'checkAvailable');
    await this.handler.validateName();
    let called = this.handler.checkAvailable.calls.allArgs()[0][0];
    expect(called).toEqual('username');
  });

  it('test-validateEmail-bad-email', async function(){
    spyOn(this.handler, 'checkAvailable');
    let email = $('#email');
    email.val('bla');
    await this.handler.validateEmail();
    expect(this.handler.checkAvailable).not.toHaveBeenCalled();
  });

  it('test-validateEmail-ok', async function(){
    spyOn(this.handler, 'checkAvailable');
    let email = $('#email');
    email.val('bla@nada.com');
    await this.handler.validateEmail();
    let called = this.handler.checkAvailable.calls.allArgs()[0][0];
    expect(called).toEqual('email');
  });

  it('test-validatePassword-not-valid', function(){
    let passwd_el = $('#password');
    passwd_el.val('asd');
    this.handler.validatePassword();
    expect(this.handler._valid['password']).toBe(false);
  });

  it('test-validatePassword-valid', function(){
    let passwd_el = $('#password');
    passwd_el.val('asd12345');
    this.handler.validatePassword();
    expect(this.handler._valid['password']).toBe(true);
  });

});
