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

var RED = 'rgb(226, 112, 123)';

function _disable_button(){
  // disables the login button

  let btn = jQuery('#btn-login');
  let btn_spinner = jQuery('#login-btn-spinner');
  let btn_text = jQuery('#login-btn-text');
  btn.addClass('disabled');
  btn_spinner.show();
  btn_text.hide();
}

function _enable_button(){
  // enables the login button

  let btn = jQuery('#btn-login');
  let btn_spinner = jQuery('#login-btn-spinner');
  let btn_text = jQuery('#login-btn-text');
  btn.removeClass('disabled');
  btn_spinner.hide();
  btn_text.show();
}

function _showErrorMessage(){
  // shows the invalid credentials message

  let msg_container = jQuery('#login-error-msg-container');
  msg_container.animate({'color': RED}, 500);
}

function _hideErrorMessage(){
  // hides the invalid  credential message

  let msg_container = jQuery('#login-error-msg-container');
  msg_container.animate({'color': 'white'}, 500);

}

function getRedir(){
  let params = new URLSearchParams(window.location.search.slice(1));
  return params.get('redirect') || '/';
}

function _getHeaders(){
  let xsrf_token = Cookies.get('_xsrf');
  let headers = {'X-XSRFToken': xsrf_token};
  return headers;
}

async function doLogin(_location=null){
  let form = jQuery('#form-signin');
  let location = _location || window.location;

  if (!form.valid()){
    return false;
  }

  _disable_button();

  let headers = _getHeaders();
  let username_or_email = jQuery('#inputUsername').val().trim();
  let password = jQuery('#inputPassword').val().trim();

  let url = window.location.href;
  let data = {'url': url,
	      'data': JSON.stringify({'username_or_email': username_or_email,
				      'password': password}),
	      'headers': headers,
	      'type': 'post'};
  let r;
  try{
    // tries to authenticate and redirect to the main page.
    await jQuery.ajax(data);
    let redir = getRedir();
    location.replace(redir);
    r = true;
  }catch (e){
    // if something goes wrong, shows the error message.
    _enable_button();
    _showErrorMessage();
    r = false;
  };
  return r;
}

function _getResetPasswordURL(){
  let protocol = window.location.protocol;
  let hostname = window.location.hostname;
  let path = '/reset-password?token={token}';

  let url = protocol + '//' + hostname + path;
  return url;
}

async function requestChangePassword(){
  let url = TOXIC_USER_PUBLIC_API_URL + 'request-password-reset';
  let email = $('#change-password-email').val();
  let reset_url = _getResetPasswordURL();
  let headers = _getHeaders();
  let data = {url: url, data: JSON.stringify({email: email,
					      reset_password_url: reset_url}),
	      headers: headers,
	      type: 'post'};

  let modal = $('#forgotPasswordModal');
  try{
    await $.ajax(data);
    modal.modal('hide');
    utils.showSuccessMessage(i18n(
      'An email was sent to the address'));
  }catch(e){
    modal.modal('hide');
    if (e.status == 400){
      utils.showErrorMessage(i18n('This email does not have an account'));
    }else{
      utils.showErrorMessage(i18n('Error requesting password reset'));
    }
  }
}


async function changePasswordWithToken(){
  let url = TOXIC_USER_PUBLIC_API_URL + 'change-password-with-token';

  let passwd = $('#inputPassword').val();
  let confirm = $('#inputPasswordConfirm').val();

  if (passwd != confirm){
    utils.showErrorMessage(i18n('Password confirmation does not match'));
    return;
  }

  let token = $('#token').val();
  let headers = _getHeaders();
  let json_data = JSON.stringify({'password': passwd,
				  'token': token});
  let data = {url: url, data: json_data,
	      headers: headers,
	      type: 'post'};

  $('#change-password-btn-text').hide();
  $('#change-password-btn-spinner').show();
  try{
    await $.ajax(data);
    $('#change-password-input-container').hide();
    $('#password-changed-message').show();
  }catch(e){
    if (e.status == 400){
      utils.showErrorMessage(i18n('Invalid token'));
    }else{
      utils.showErrorMessage(i18n('Error changing password'));
    }
  }

  $('#change-password-btn-text').show();
  $('#change-password-btn-spinner').hide();

}

// Connecting to events

jQuery('.login-form-control').keypress(function(){
  // Hides the error message on keypress if the message is
  // displayed
  let msg_container = jQuery('#login-error-msg-container');
  let style = msg_container.attr("style");

  if( style && style != "color: rgb(255, 255, 255);"){
    // hides if the message is not white
    _hideErrorMessage();
  }

});

// form validation
jQuery('#form-signin').validate({
  errorPlacement: function(error, element){
    element.addClass('form-control-error');
  },

  errorClass: "form-control-error",
  focusCleanup: true,
});

// button action
jQuery('#btn-login').on('click', function(){
  doLogin();
});


$('#btn-request-password-reset').on('click', function(){
  requestChangePassword();
});

$('#forgotPasswordModal').on('show.bs.modal', function(){
  $('#change-password-email').val('');
});


$('#btn-change-password').on('click', function(){
  changePasswordWithToken();
});
