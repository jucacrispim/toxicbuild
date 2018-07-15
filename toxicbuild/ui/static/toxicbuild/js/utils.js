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
SETTIMEOUT_MILIS = 5000;

var utils = {
  success_message: jQuery('.alert-success'),
  error_message: jQuery('.alert-danger'),

  hideSuccessMessage: function(message_container){
    var self = this;
    message_container.fadeOut();
  },

  showSuccessMessage: function(message){
    var self = this;
    jQuery('#success-container').text(message);
    self.success_message.fadeIn();
    setTimeout(function(){self.hideSuccessMessage(self.success_message);},
	       SETTIMEOUT_MILIS);
  },

  hideErrorMessage: function(message_container){
    var self = this;
    message_container.fadeOut();
  },

  showErrorMessage: function(message){
    var self = this;
    jQuery('#error-container').text(message);
    self.error_message.fadeIn();
    setTimeout(function(){self.hideErrorMessage(self.error_message);},
	       SETTIMEOUT_MILIS);
  },

  _canvas: document.createElement("canvas"),

  _get_text_width: function(text){
    var context = utils._canvas.getContext("2d");
    context.font = '400 16px Arial,sans-serif';
    var metrics = context.measureText(text);
    return metrics.width;

  },

  checkboxToggle: function(el){
    el.bootstrapToggle();
    let on_text = el.data('on');
    let off_text = el.data('off');
    let text = on_text > off_text ? on_text : off_text;
    let width = utils._get_text_width(text) + 30;
    el.parent().attr('style', 'width: ' + width + 'px;');
  }

};
