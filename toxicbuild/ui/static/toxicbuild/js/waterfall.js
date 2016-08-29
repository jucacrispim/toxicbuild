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

jQuery('#buildsetDetailsModal').on('show.bs.modal', function (event) {
  var button = jQuery(event.relatedTarget);
  var commit = button.data('buildset-commit');
  var author = button.data('buildset-commit-author');
  var title = button.data('buildset-commit-title');
  var created = button.data('buildset-created');
  var branch = button.data('buildset-branch');

  var modal = jQuery(this)
  modal.find('#buildset-commit').text(commit);
  modal.find('#buildset-commit-author').text(author);
  modal.find('#buildset-commit-title').text(title);
  modal.find('#buildset-created').text(created);
  modal.find('#buildset-branch').text(branch);
});

jQuery('.btn-rebuild-buildset').on('click', function(event){
  var button = jQuery(this);
  var named_tree = button.data('buildset-commit');
  var branch = button.data('buildset-branch');
  var url = '/api/repo/start-build';
  var data = {name: 'ToxicBuild', named_tree: named_tree, branch: branch};
  utils.sendAjax('post', url, data);
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
