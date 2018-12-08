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

describe('UserTest', function(){

  beforeEach(function(){
    this.user = new User();
  });

  it('test-changePassword', async function(){
    spyOn(this.user, '_post2api');
    let old_password = '123';
    let new_password = '456';
    let e = [this.user._api_url + 'change-password',
	     {old_password: old_password,
	      new_password: new_password}];
    await this.user.changePassword(old_password, new_password);
    let c = this.user._post2api.calls.allArgs()[0];
    expect(c).toEqual(e);
  });
});


describe('UserSettingsViewTest', function(){

  beforeEach(function(){
    this.view = new UserSettingsView();
    let cp = affix('input#current-password');
    cp.val('123');
    affix('input#new-password');
    affix('input#confirm-new-password');
    affix('#btn-change-password');
    affix('#change-password-btn-spinner');
    affix('#change-password-btn-text');

  });

  it('test-changePassword-bad-confirm', async function(){
    $('#new-password').val('456');
    $('#confirm-new-password').val('56');
    spyOn(utils, 'showErrorMessage');
    let r = await this.view.changePassword();
    expect(r).toBe(false);
    expect(utils.showErrorMessage).toHaveBeenCalled();
  });

  it('test-changePassword-error', async function(){

    $('#new-password').val('456');
    $('#confirm-new-password').val('456');
    spyOn(utils, 'showErrorMessage');
    spyOn(this.view.model, 'changePassword').and.throwError();
    let r = await this.view.changePassword();
    expect(r).toBe(false);
    expect(utils.showErrorMessage).toHaveBeenCalled();

  });

  it('test-changePassword-ok', async function(){

    $('#new-password').val('456');
    $('#confirm-new-password').val('456');
    spyOn(utils, 'showSuccessMessage');
    spyOn(this.view.model, 'changePassword');
    let r = await this.view.changePassword();
    expect(r).toBe(true);
    expect(utils.showSuccessMessage).toHaveBeenCalled();

  });

});
