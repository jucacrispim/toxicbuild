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

var TOXIC_USER_API_URL = window.TOXIC_API_URL + 'user/';


class User extends BaseModel{

  constructor(attributes, options){
    super(attributes, options);
    this._api_url = TOXIC_USER_API_URL;
  }

  async changePassword(old_password, new_password){
    let body = {old_password: old_password, new_password: new_password};
    let url = this._api_url + 'change-password';
    return this._post2api(url, body);
  }
}


class UserSettingsView extends Backbone.View{

  constructor(options){
    options = options || {};
    options.model = options.model || new User();
    super(options);
    this.model = options.model;
  }

  async render_all(){
    let self = this;

    $('#btn-change-password').on('click', function(){
      self.changePassword();
    });
    $('.wait-toxic-spinner').hide();
    $('#user-settings-container').fadeIn(300);
  }

  _checkPasswordConfirm(password, confirm_password){
    return password == confirm_password;

  }

  async changePassword(){
    let current_password = $('#current-password');
    let new_password = $('#new-password');
    let confirm_password = $('#confirm-new-password');
    if (!this._checkPasswordConfirm(new_password.val(),
				    confirm_password.val())){
      utils.showErrorMessage(i18n('Password confirmation does not match'));
      return false;
    }

    let btn = $('#btn-change-password');
    let spinner = $('#change-password-btn-spinner');
    let text = $('#change-password-btn-text');

    btn.prop('disabled', true);
    text.hide();
    spinner.show();
    try{
      await this.model.changePassword(current_password.val(),
				      new_password.val());
      spinner.hide();
      text.show();
      btn.prop('disabled', false);
      current_password.val('');
      new_password.val('');
      confirm_password.val('');
      utils.showSuccessMessage(i18n('Password changed'));
    }catch(e){
      spinner.hide();
      text.show();
      btn.prop('disabled', false);
      utils.showErrorMessage(i18n('Error changing password'));
      return false;
    }

    return true;
  }
}
