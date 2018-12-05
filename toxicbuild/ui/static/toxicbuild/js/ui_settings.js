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


class UISettingsView extends Backbone.View{

  constructor(options){
    super(options);
    this.cookie_name = 'dark-theme';
  }

  render_all(){
    let self = this;
    let check_el = $('.form-check-input');

    this._setCheckbox(check_el);

    check_el.change(function(){
      let el = $($('.form-check-input')[0]);
      let enabled = el.is(':checked');
      self.setThemeCookie(enabled);
    });

    $('.wait-toxic-spinner').hide();
    $('#ui-settings-container').fadeIn(300);
  }

  _hasThemeCookie(){
    return Cookies.get(this.cookie_name);
  }

  _setCheckbox(check_el){
    if (this._hasThemeCookie()){
      check_el.prop('checked', true);
    }
  }

  setThemeCookie(enabled){
    if (enabled){
      $('body').addClass(this.cookie_name);
      Cookies.set(this.cookie_name, true);
    }else{
      $('body').removeClass(this.cookie_name);
      Cookies.remove(this.cookie_name);
    }

  }

}
