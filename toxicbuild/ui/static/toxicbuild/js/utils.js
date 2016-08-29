// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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


TOXICDEBUG = false;

var utils = {
  success_message: jQuery('.alert-success'),
  error_message: jQuery('.alert-danger'),

  hideSuccessMessage: function(message_container){
    var self = this;
    message_container.fadeOut();
    jQuery('#success-container').text('');
  },

  showSuccessMessage: function(message){
    var self = this;
    jQuery('#success-container').text(message);
    self.success_message.fadeIn();
    setTimeout(function(){self.hideSuccessMessage(self.success_message)},
	       3000);
  },

  hideErrorMessage: function(message_container){
    var self = this;
    message_container.fadeOut();
    jQuery('#error-container').text('');
  },

  showErrorMessage: function(message){
    var self = this;
    jQuery('#error-container').text(message);
    self.error_message.fadeIn();
    setTimeout(function(){self.hideErrorMessage(self.error_message)},
	       3000);
  },

  sendAjax: function(type, url, data, success_cb, error_cb, async){
    var self = this;
    if (async == undefined){
      async = true;
    }

    $.ajax({
      type: type,
      url: url,
      data: data,
      async: async,
      traditional: true,
      success: success_cb,
      error: error_cb,
    });
  },

  log: function(msg){
    if (TOXICDEBUG){
      console.log(msg);
    }
  },
};
