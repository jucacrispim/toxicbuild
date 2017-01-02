var CURRENT_STEP_SHOWN = null;

jQuery('#stepDetailsModal').on('show.bs.modal', function (event) {
  var button = jQuery(event.relatedTarget);
  var command = button.data('step-command');
  var output = button.data('step-output');
  var status = button.data('step-status');
  var start = button.data('step-start');
  var end = button.data('step-end');
  var uuid = button.data('step-uuid');

  var modal = jQuery(this)
  modal.find('#step-command').text(command);
  modal.find('#step-output').text(output);
  modal.find('#step-status').text(status);
  modal.find('#step-start').text(start);
  modal.find('#step-end').text(end);
  CURRENT_STEP_SHOWN = uuid;
  var element = document.getElementById('step-output');
  element.scrollIntoView(false);
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

function rebuildBuildset(button){
  var named_tree = button.data('buildset-commit');
  var branch = button.data('buildset-branch');
  var url = '/api/repo/start-build';
  var repo_name = jQuery('#waterfall-repo-name').val();
  var data = {name: repo_name, named_tree: named_tree, branch: branch};
  utils.log('rebuild buildset for ' + repo_name);
  var success_cb = function(response){
    utils.showSuccessMessage('Buildset re-scheduled.');
  };

  var error_cb = function(response){
    utils.showErrorMessage('Error re-scheduling buildset!');
  };

  utils.sendAjax('post', url, data, success_cb, error_cb);
}

jQuery('.btn-rebuild-buildset').on('click', function(event){
  var button = jQuery(this);
  rebuildBuildset(button);
});


function rebuildBuild(button){
  var named_tree = button.data('buildset-commit');
  var branch = button.data('buildset-branch');
  var builder_name = button.data('builder-name');
  var url = '/api/repo/start-build';
  var repo_name = jQuery('#waterfall-repo-name').val();
  utils.log('rebuild build for ' + repo_name);
  var data = {name: repo_name, named_tree: named_tree, branch: branch,
	      builder_name: builder_name};
  var success_cb = function(response){
    utils.showSuccessMessage('Build re-scheduled.')
  };

  var error_cb = function(response){
    utils.showErrorMessage('Error re-scheduling build!')
  };

  utils.sendAjax('post', url, data, success_cb, error_cb);
}
jQuery('.btn-rebuild-build').on('click', function(event){
  var button = jQuery(this);
  rebuildBuild(button);
});


function sticky_relocate() {
  var BUILDER_SIZE = [];
  jQuery('.builder').each(function (){
    BUILDER_SIZE.push(jQuery(this).outerWidth());
  });
  var i = 0
  jQuery('.builder').each(function(){
    var window_top = jQuery(window).scrollTop();
    var div_top = jQuery(this).offset().top;
    if (window_top >= div_top && window_top > 52){
      jQuery(this).outerWidth(BUILDER_SIZE[i]);
      jQuery(this).addClass('builder-stick');
    }
    else{
      jQuery('.builder').each(function(){
      	jQuery(this).removeClass('builder-stick');
      });

    }
    i += 1;
  });
}

jQuery(function(){
  // jQuery('.builder').each(function (){
  //   BUILDER_SIZE.push(jQuery(this).outerWidth());
  // });
  $(window).scroll(sticky_relocate);
});


var BUILDSET_TEMPLATE  = `
    <tr class="waterfall-row">
      <td class="buildsets-column">
	<ul>
	  <li class="buildset" id="buildset-{{buildset.id}}">
	    commit: {{buildset.commit8}}<br/>
	    branch: {{buildset.branch}}<br/>
	    <button type="button" class=" btn btn-default btn-rebuild btn-transparent btn-buildset-details btn-sm"
		    data-toggle="modal"
		    data-target="#buildsetDetailsModal"
		    data-dismiss="modal"
		    data-buildset-commit="{{buildset.commit}}"
		    data-buildset-branch="{{buildset.branch}}"
		    data-buildset-commit-author="{{buildset.author}}"
		    data-buildset-commit-title="{{buildset.title}}"
		    data-buildset-created="{{buildset.created}}">
	      <span data-toggle="tooltip" title="Buildset details" data-placement="right">

		<span class="glyphicon glyphicon-modal-window" aria-hidden="true"></span>
	      </span>
	    </button>

	    <span data-toggle="tooltip" title="Re-schedule buildset" data-placement="right">
	      <button type="button" class="btn btn-default btn-rebuild btn-transparent btn-rebuild-buildset btn-sm"
		      data-buildset-commit="{{buildset.commit}}"
		      data-buildset-branch="{{buildset.branch}}">

		<span class="glyphicon glyphicon-repeat" aria-hidden="true"></span>
	      </button>
	     </span>

	  </li>
	</ul>
      </td>
    </tr>
  `

var BUILD_TEMPLATE = `
<ul>
  <li class="step step-{{build.status}}" id="build-info-{{build.id}}">
    Build - {{build.status}}
    <i class="fa fa-cog fa-spin fa-3x fa-fw toxic-spinner-main" id="spinner-build-{{build.uuid}}" style="display:none"></i>
    <span data-toggle="tooltip" title="Re-schedule build" data-placement="right" style="display:none" class="rebuild-icon">
      <button type="button" class="btn btn-default btn-rebuild btn-transparent btn-rebuild-build btn-sm"
        data-buildset-commit="{{buildset.commit}}"
        data-buildset-branch="{{buildset.branch}}"
        data-builder-name="{{build.builder.name}}">

        <span class="glyphicon glyphicon-repeat" aria-hidden="true"></span>
      </button>
    </span>
  </li>
</ul>
  `;

var STEP_TEMPLATE = `
	  <li class="step step-{{step.status}}" id="step-{{step.uuid}}">
	    <div class="build-step-info-container">
	      {{step.name}} - {{step.status}}
	      <button type="button" class="btn btn-default btn-step-details btn-transparent btn-sm"
		      data-toggle="modal"
		      data-target="#stepDetailsModal"
		      data-dismiss="modal"
                      data-step-uuid="{{step.uuid}}"
		      data-step-command="{{step.command}}"
		      data-step-output="{{step.output}}"
		      data-step-status="{{step.status}}"
		      data-step-start="{{step.started}}"
		      data-step-end="{{step.finished}}">
		<span data-toggle="tooltip" title="Step details" data-placement="right">
		  <span class="glyphicon glyphicon-modal-window" aria-hidden="true"></span>
		</span>

	      </button>
	    </div>
	  </li>
`

var BUILDERS = [];

function StepOutputSentinel(uuid){
  // Entity responsible for changing the step output
  // acording to the info sent by the server.

  var host = window.location.host;
  var obj = {
    url: 'ws://' + host + '/api/socks/step-output?uuid=' + uuid,
    ws: null,
    old_output: '{{step.output}}',

    init: function(){
      var self = this;
      self.ws = new WebSocket(self.url);
      self.ws.onmessage = function(event){
	self.handleEvent(self, event);
      };
    },

    handleEvent: function(self, event){
      var data = jQuery.parseJSON(event.data);
      utils.log(data.event_type);
      var step_el = jQuery('#step-' + data.uuid);
      var button = jQuery('button', step_el);
      self.old_output = button.data('step-output');
      var new_output = self.old_output + data.output;
      button.data('step-output', new_output);
      self.old_output = new_output;
      if (CURRENT_STEP_SHOWN == data.uuid){
	var modal = jQuery('#stepDetailsModal');
	modal.find('#step-output').text(new_output);
	//jQuery("#step-output").scrollTop($("#step-output")[0].scrollHeight);
      }
    },

  };
  obj.init();
  return obj
};

function WaterfallManager(){
  var id = jQuery('#waterfall-repo-id').val();
  var host = window.location.host;

  obj = {
    url: 'ws://' + host + '/api/socks/builds?repository_id=' + id,
    ws: null,
    _build_last_step: {},
    _step_started_queue: [],
    _step_finished_queue: [],
    _build_started_queue: [],
    _build_finished_queue: [],
    _step_sentinels: {},
    _step_output: {},

    init: function(){
      var self = this;
      self.ws = new WebSocket(self.url);
      self.ws.onmessage = function(event){
	self.handleEvent(self, event);
      };
    },

    handleEvent: function(self, event){

      var data = jQuery.parseJSON(event.data);
      utils.log(data.event_type);
      if (data.event_type == 'build_added'){
	self.handleBuildAdded(data);
      }else if (data.event_type == 'build_started'){
	self.handleBuildStarted(data);
      }else if (data.event_type == 'build_finished'){
	self.handleBuildFinished(data);
      }else if (data.event_type == 'step_started'){
	self.handleStepStarted(data);
      }else if (data.event_type == 'step_finished'){
	self.handleStepFinished(data);
      }
    },

    handleStepStarted: function(step, from_queue){
      // insert the info about a step in the waterfall
      var self = this;
      var template = STEP_TEMPLATE.replace(/{{step.uuid}}/g, step.uuid);
      template = template.replace(/{{step.status}}/g, step.status);
      template = template.replace(/{{step.name}}/g, step.name);
      template = template.replace(/{{step.command}}/g, step.command);
      //template = template.replace(/{{step.output}}/g, "No output...");
      template = template.replace(/{{step.started}}/g, step.started);
      template = template.replace(/{{step.finished}}/g, 'Step still running');

      var build = step.build
      var build_el = jQuery('#build-info-' + build.uuid);
      // if there is no build_el we store the step in a query and after
      // the build is present we insert the build info.
      if (!build_el.length){
	self._step_started_queue.push(step);
	return false;
      };
      // here we handle the case when the information about one step
      // arrived before the information about a previous step.
      if ((typeof self._build_last_step[build.uuid] != 'undefined' &&
      	   self._build_last_step[build.uuid] < step.index -1) ||
      	  (typeof self._build_last_step[build.uuid] == 'undefined' &&
	   step.index != 0)){

	var steps_count = jQuery('.build-step-info-container',
				 build_el.parent()).length;
      	if (self._step_started_queue.indexOf(step) < 0 &&
	    steps_count - 1 > step.index){
	  utils.log('step enqueued: ' + step.uuid);
      	  self._step_started_queue.push(step);
      	  return false;
      	};
      };
      template = jQuery(template);
      template.hide();
      build_el.parent().append(template);
      template.slideDown('slow');
      self._step_sentinels[step.uuid] = StepOutputSentinel(step.uuid)
      self._build_last_step[build.uuid] = step.index;
      if (!from_queue){
	self._handleStepQueue(build);
      }
    },

    handleStepFinished: function(step){
      var self = this;

      var step_el = jQuery('#step-' + step.uuid);
      if (!step_el.length){
	self._step_finished_queue.push(step);
	return false
      };

      try{
      	self._step_sentinels[step.uuid].ws.close();
      } catch(e){
      	utils.log(e);
      };

      delete self._step_sentinels[step.uuid];
      var html = step_el.html();
      step_el.removeClass('step-running').addClass('step-' + step.status);
      html = html.replace('Step still running', step.finished);
      html = html.replace('{{step.output}}', step.output.replace(/"/g, "'"));
      html = html.replace(/running/g, step.status);
      step_el.html(html);
    },

    handleBuildStarted: function(build){
      var self = this;

      var build_el = jQuery('#build-info-' + build.uuid);

      if (build_el.length == 0){
	self._build_started_queue.push(build);
	return false;
      };

      var html = build_el.html().replace(/pending/, 'running');
      html = html.replace(/{{build.uuid}}/g, build.uuid);
      build_el.html(html);
      build_el.removeClass('step-pending').addClass('step-running');

      var spinner = jQuery('#spinner-build-' + build.uuid);
      spinner.show();

      var builder_input = jQuery('#builder-' + build.builder.id)
      var builder_status = builder_input.val();
      if (builder_status != 'running'){
	builder_input.parent().removeClass('builder-' + builder_status);
	builder_input.parent().addClass('builder-running');
	builder_input.val('running');
      }
    },

    handleBuildFinished: function(build){
      var self = this;

      var build_el = jQuery('#build-info-' + build.uuid);
      if (!build_el.length){
	self._build_finished_queue.push(build);
	return false;
      }

      var spinner = jQuery('#spinner-build-' + build.uuid);
      spinner.hide();

      build_el.html(build_el.html().replace(/running/, build.status));
      jQuery('.rebuild-icon', build_el).show();

      jQuery('.btn-rebuild-build', build_el).on('click', function(event){
	var button = jQuery(this);
	rebuildBuild(button);
      });

      build_el.removeClass('step-running').addClass('step-' + build.status);

      var builder_input = jQuery('#builder-' + build.builder.id)
      var builder_status = builder_input.val();
      builder_input.parent().removeClass('builder-running');
      builder_input.parent().removeClass('builder-pending');
      builder_input.parent().addClass('builder-' + build.status);
      builder_input.val(build.status);
    },

    handleBuildAdded: function(build){
      var self = this;
      var buildset = build.buildset;
      var buildset_li = jQuery('#buildset-' + buildset.id);
      if (!buildset_li.length){
	self._addBuildSet(buildset);
      };
      self._addBuild(build);
    },

    _handleBuildQueue: function(build){
      var self = this;
      // here we handle the started builds in queue.
      var new_builds_queue = [];
      for (i in self._build_started_queue){
	var enqueued_build = self._build_started_queue[i];
	if (enqueued_build.id == build.id){
	  self.handleBuildStarted(build);
	  self._handleStepQueue(build);
	}else{
	  new_builds_queue.push(build);
	};
      };

      // here we handle the finished builds in queue.
      var new_builds_queue = [];
      for (i in self._build_finished_queue){
	var enqueued_build = self._build_finished_queue[i];
	if (enqueued_build.id == build.id){
	  self.handleBuildFinished(build);
	  self._handleStepQueue(build);
	}else{
	  new_builds_queue.push(build);
	};
      };

      self._build_finished_queue = new_builds_queue;
    },

    _handleStepQueue: function(build){
      var self = this;

      // here we handle the started steps in queue.
      var new_steps_queue = [];
      self._step_started_queue.sort(function(a, b){return a.index - b.index});

      for (i in self._step_started_queue){
	var step = self._step_started_queue[i];
	if (step.build.id == build.id){
	  self.handleStepStarted(step, true);
	}else{
	  new_steps_queue.push(step);
	};
      };
      self._step_started_queue = new_steps_queue;

      // here we handle the finished steps in queue.
      var new_steps_queue = [];
      self._step_finished_queue.sort(function(a, b){return a.index - b.index});

      for (i in self._step_finished_queue){
	var step = self._step_finished_queue[i];
	if (step.build.id == build.id){
	  self.handleStepFinished(step);
	}else{
	  new_steps_queue.push(step);
	};
      };
      self._step_finished_queue = new_steps_queue;
    },

    _addBuildSet: function(buildset){
      var self = this;

      var template = BUILDSET_TEMPLATE.replace(/{{buildset.id}}/g, buildset.id);
      template = template.replace(/{{buildset.commit}}/g, buildset.commit);
      template = template.replace(/{{buildset.commit8}}/g, buildset.commit.slice(0, 8));
      template = template.replace(/{{buildset.author}}/g, buildset.author);
      template = template.replace(/{{buildset.branch}}/g, buildset.branch);
      template = template.replace(/{{buildset.title}}/g, buildset.title);
      template = template.replace(/{{buildset.created}}/g, buildset.created);
      var first_row = jQuery('#waterfall-first-row');
      jQuery(template).insertAfter(first_row);

      var buildset_el = jQuery('#buildset-' + buildset.id).parent().parent().parent();

      jQuery('.btn-rebuild-buildset', buildset_el).on('click', function(event){
	var button = jQuery(this);
	rebuildBuildset(button);
      });

      for (i = 0; i <= buildset.builds.length; i++){
	var builder = BUILDERS[i];
	if (!builder){return false}
	var parsed_builder = jQuery.parseJSON(builder);
	builder = parsed_builder;

	buildset_el.append('<td class="builder-column" id="build-builder-'+ builder.id +'"></td>');
      };

    },

    _addBuild: function(build){
      var self = this;
      var builder = self._getBuilder(build.builder.id);
      var buildset = build.buildset
      var build_el = jQuery('#build-builder-' + build.builder.id);

      if (!build_el.length){
	var buildset_el = jQuery('#buildset-' + buildset.id).parent().parent().parent();
	buildset_el.append('<td class="builder-column" id="build-builder-'+ build.builder.id +'"></td>');
	build_el = jQuery('#build-builder-' + build.builder.id);
      };

      var template = BUILD_TEMPLATE.replace(/{{build.status}}/g, build.status);
      template = template.replace(/{{buildset.commit}}/g, buildset.commit);
      template = template.replace(/{{build.id}}/g, build.uuid);
      template = template.replace(/{{buildset.branch}}/g, buildset.branch);
      var builder_name = builder ? builder.name : 'new-builder';
      template = template.replace(/{{build.builder.name}}/g, builder_name);
      jQuery(build_el).append(template);
      self._handleBuildQueue(build);
      self._handleStepQueue(build);
    },

    _getBuilder: function(builder_id){
      for (i = 0; i < BUILDERS.length; i++){
	var builder = jQuery.parseJSON(BUILDERS[i]);
	if (builder_id == builder.id){
	  return builder;
	};
      };
    },
  };

  obj.init();
  return obj;
};

var manager = WaterfallManager();
