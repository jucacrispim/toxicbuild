// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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


TOXICDEBUG = false;
SETTIMEOUT_MILIS = 5000;

var utils = {
  error_message: jQuery('.alert-danger'),
  success_message: jQuery('.alert-success'),


  hideSuccessMessage: function(){
    var self = this;
    self.success_message.fadeOut();
  },

  sleep: function(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  showSuccessMessage: function(message){
    var self = this;
    jQuery('#success-container').text(message);
    self.success_message.fadeIn();
    setTimeout(function(){self.hideSuccessMessage();},
	       SETTIMEOUT_MILIS);
  },

  hideErrorMessage: function(message_container){
    var self = this;
    self.error_message.fadeOut();
  },

  showErrorMessage: function(message){
    var self = this;
    jQuery('#error-container').text(message);
    self.error_message.fadeIn();
    setTimeout(function(){self.hideErrorMessage();},
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
  },

  get_badge_class: function(status){
    let badge_classes = {'ready': 'secondary',
			 'running': 'primary',
			 'exception': 'exception',
			 'success': 'success',
			 'pending': 'pending',
			 'no config': 'secondary',
			 'clone-exception': 'exception'};
    let status_class = badge_classes[status] || status;
    let badge_class = 'badge-' + status_class;
    return badge_class;
  },

  setBuildsForBuildSet: function(buildset){
    buildset.attributes['builds'] = buildset._getBuilds(buildset.get('builds'));
  },

  binarySearch: function(arr, value){
    let low = 0;
    let high = arr.length - 1;
    let mid;

    while (low <= high){
      mid = Math.floor((low + high) / 2);

      let val = arr[mid];

      if (val < value){
	low = mid + 1;
      }
      else if (val > value){
	high = mid - 1;
      }
      else{
	return mid;
      }
    };
    return -(low);
  },

  wrapperSlideDown: function(el, ms, cb){
    el.wrapInner('<div style="display: none;" />')
      .parent()
      .find(el.prop('tagName') + ' > div')
      .slideDown(ms, function(){
	cb = cb || function(){};
	cb();
	var $set = $(this);
	$set.replaceWith($set.contents());
      });
  },

  async rescheduleBuildSet(buildset, el_container, builder_name=null){
    let repo = new Repository({'id': buildset.get('repository').id});
    let branch = buildset.get('branch');
    let named_tree = buildset.get('commit');

    let spinner = $('.spinner-reschedule-buildset', el_container);
    let retry_btn = $('.fa-redo', el_container);
    retry_btn.hide();
    spinner.show();
    try{
      await repo.start_build(branch, builder_name, named_tree);
      if (builder_name){
	utils.showSuccessMessage(i18n('Build re-scheduled'));
      }else{
	utils.showSuccessMessage(i18n('Buildset re-scheduled'));
      }

    }catch(e){
      utils.showErrorMessage(i18n('Error re-scheduling buildset'));
    }
    retry_btn.show();
    spinner.hide();
  },

  formatSeconds(secs){
    let d = new Date(secs * 1000);
    return d.toISOString().substr(11, 8);
  },

  setTheme(){
    var cookie = Cookies.get('dark-theme');
    if(cookie){
      $('body').removeClass('dark-theme').addClass('dark-theme');
    }
    else{
      $('body').removeClass('dark-theme');
    }

  },

  async loadTranslations(static_url){
    let locale = Cookies.get('ui_locale');
    if (!locale){
      return false;
    }
    if (locale == 'en_US'){
      i18n.translator.reset();
      return true;
    }

    let r;
    let kw = {url: static_url + 'toxicbuild/i18n/' + locale + '.json',
	      'Content-Type': 'application/json'};
    try{
      r = await $.ajax(kw);
    }catch(e){
      return false;
    }
    i18n.translator.add(r);
    return true;
  },

  getClientTZ(){
    let tz;
    try{
      tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    }catch(e){
      tz = 'UTC';
    }
    return tz;
  },

  setTZCookie(){
    let tz = utils.getClientTZ();
    Cookies.set('tzname', tz);
  }

};


class TimeCounter{

  constructor(){
    this.secs = 0;
    this._stop = false;
  }

  async start(cb){
    while (!this._stop){
      cb(this.secs);
      await utils.sleep(1000);
      this.secs += 1;
    }
    this._stop = false;
  }

  stop(){
    this._stop = true;
  }
}
