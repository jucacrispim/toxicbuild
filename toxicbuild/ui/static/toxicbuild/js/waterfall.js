jQuery('#stepDetailsModal').on('show.bs.modal', function (event) {
  var button = jQuery(event.relatedTarget);
  var command = button.data('step-command');
  var output = button.data('step-output');
  var status = button.data('step-status');
  var start = button.data('step-start');
  var end = button.data('step-end');

  var modal = jQuery(this)
  modal.find('#step-command').text(command);
  modal.find('#step-output').text(output);
  modal.find('#step-status').text(status);
  modal.find('#step-start').text(start);
  modal.find('#step-end').text(end);
});

var BUILDER_SIZE = null;

function sticky_relocate() {
  jQuery('.builder').each(function(){
    var window_top = jQuery(window).scrollTop();
    var div_top = jQuery(this).offset().top;
    console.log(div_top, window_top);
    if (window_top >= div_top && window_top > 52){
      jQuery(this).outerWidth(BUILDER_SIZE);
      jQuery(this).addClass('builder-stick');
    }
    else{
      jQuery('.builder').each(function(){
      	jQuery(this).removeClass('builder-stick');
      });

    }
  });
}

jQuery(function(){
  BUILDER_SIZE = jQuery(jQuery('.builder')[0]).outerWidth();
  $(window).scroll(sticky_relocate);
});
