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

async function doLogin(_location=null){
  let form = jQuery('#form-signin');
  let location = _location || window.location;

  if (!form.valid()){
    return false;
  }

  _disable_button();

  let xsrf_token = Cookies.get('_xsrf');
  let headers = {'X-XSRFToken': xsrf_token};
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
    location.replace('/');
    r = true;
  }catch (e){
    // if something goes wrong, shows the error message.
    _enable_button();
    _showErrorMessage();
    r = false;
  };
  return r;
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
