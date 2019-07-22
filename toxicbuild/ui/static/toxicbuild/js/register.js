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

var TOXIC_USER_PUBLIC_API_URL = window.TOXIC_API_URL + 'public/user/';


class RegisterHandler{

  constructor(){
    this._listen2events();
    this._valid = {'username': false, 'email': false, 'password': false};
  }

  async _isAvailable(what){
    let value = $('#' + what).val();
    let url = TOXIC_USER_PUBLIC_API_URL + 'check?' + what + '=' + value;
    let r = await $.ajax({'url': url});
    return !r['check-exists'];
  }

  async checkAvailable(what){
    let spinner = $('#register-available-spinner');
    spinner.show();
    let r = await this._isAvailable(what);
    spinner.hide();
    if (r){
      this._valid[what] = true;
    }else{
      $('#register-available-fail').show();
      this._valid[what] = false;
      this._showErrorInfo(what + ' is not available');
    }
    this.handleButton();
  }

  _redir(url){
    window.location = url;
  }

  _showErrorInfo(text){
    let error_msg_container = $('#register-error-msg');
    error_msg_container.text(text);
    $('#register-available-fail').show();
    error_msg_container.show();
  }

  async register(){
    let username = $('#username').val();
    let email = $('#email').val();
    let password = $('#password').val();
    let data = {'username': username, 'email': email,
		'password': password};

    let xsrf_token = Cookies.get('_xsrf');
    let headers = {'X-XSRFToken': xsrf_token};

    try{
      await $.ajax({'url': TOXIC_USER_PUBLIC_API_URL, 'type': 'post',
		    'data': JSON.stringify(data), 'headers': headers});
      this._redir('/');
    }catch(e){
      utils.showErrorMessage('Error while signin up!');
    }
  }

  handleButton(){
    let btn = $('#btn-register');
    if (this.is_valid()){
      btn.prop('disabled', false);
      $('#register-available-ok').show();
    }else{
      btn.prop('disabled', true);
    }
  }

  is_valid(){
    for (let i in this._valid){
      let is_valid = this._valid[i];
      if (!is_valid){
	return false;
      }
    }
    return true;
  }

  _cleanInfo(){
    $('.register-info-icon').hide();
    let error_msg_container = $('#register-error-msg');
    error_msg_container.hide();
  }

  async validateName(){
    this._cleanInfo();
    await this.checkAvailable('username');
  }

  async validateEmail(){
    this._cleanInfo();
    let regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
    let email = $('#email').val();
    let is_valid = regex.test(email);
    if (!is_valid){
      this._showErrorInfo('Invalid email');
      this._valid['email'] = false;
      return;
    }
    await this.checkAvailable('email');
  }

  validatePassword(){
    this._cleanInfo();
    let passwd = $('#password').val();
    if (passwd.length < 8){
      this._valid['password'] = false;
      this._showErrorInfo('Password must be at least 8 characters long');
    }else{
      this._valid['password'] = true;
    }
    this.handleButton();
  }

  _listen2events(){
    let self = this;

    let check_name = _.debounce(function(){
      self.validateName();}, 700);
    let check_email = _.debounce(function(){
      self.validateEmail();}, 700);
    let check_password = _.debounce(function(){
      self.validatePassword();}, 700);

    $('#username').on('input', function(e){
      check_name();
    });

    $('#email').on('input', function(e){
      check_email();
    });

    $('#password').on('input', function(e){
      check_password();
    });

    $("#btn-register").on('click', function(e){
      self.register();
    });

  }
}
