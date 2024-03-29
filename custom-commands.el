(require 'pdj-utils)
(require 'pdj-venv)
(require 'pdj-python)
(require 'filenotify)

(defcustom toxic:test-env-dir (expand-file-name "~/.emacs-toxictest/")
  "Directory for the toxicbuild test environment.")

(defcustom toxic:test-env-path (concat toxic:test-env-dir "ci/")
  "Path for the toxicbuild test environment")

(defcustom toxic:test-venv-name "toxictest"
  "Name of the virtualenv for the test environment.")

(defcustom toxic:original-venv-name "toxicbuild"
  "Name of the virutalenv for the acutal code")

(defcustom toxic:py-exec "/usr/bin/python3" "Python executable")

(defcustom toxic:py-venv-exec
  (concat "~/.virtualenvs/" toxic:test-venv-name "/bin/python")
  "Python executable for the test virtualenv")

(defcustom toxic:create-test-env-command
  (concat toxic:py-venv-exec " ./scripts/toxicbuild create ")
  "Command to create a new test environment for toxicbuild.")

(defcustom toxic:slave-buffer-name "toxicslave"
  "Toxicslave buffer's name")

(defcustom toxic:master-buffer-name "toxicmaster"
  "Toxicmaster buffer's name")

(defcustom toxic:poller-buffer-name "toxicpoller"
  "Toxicpoller buffer's name")

(defcustom toxic:secrets-buffer-name "toxicsecrets"
  "Toxicsecrets buffer's name")

(defcustom toxic:integrations-buffer-name "toxicintegrations"
  "Toxicbuild integrations buffer's name")

(defcustom toxic:output-buffer-name "toxicoutput"
  "Toxicbuild output buffer's name")

(defcustom toxic:webui-buffer-name "toxicwebui"
  "Toxicweb ui buffer's name")

(defcustom toxic:run-all-tests-command
  "sh ./build-scripts/run_all_tests.sh --with-integrations"
  "The command used to run all tests in toxicubuild.")

(defcustom toxic:loglevel "debug"
  "Log level for toxicbuild servers")

(defvar toxic:bootstrap-buffer-name "toxic-bootstrap")


(defun toxic:run-all-tests ()
  "Runs tests using `pdj:test-command'. If test-args, concat it to
   the test command."

  (interactive)

  (defvar toxic--test-command)
  (if toxic:run-all-tests-command
      (let ((toxic--test-command toxic:run-all-tests-command))
	(pdj:compile-on-project-directory toxic--test-command))

    (message "No toxic:run-all-tests-command. You have to customize this.")))



(defun toxic:custom-keyboard-hooks ()
  "Custom key combinations for toxicbuild"

  (local-set-key (kbd "C-c t") 'toxic:run-all-tests))


(defun toxic:--create-venv ()

  (pdj:print "Installing dependencies first.\n")
  (pdj:print "This is going to take a while. Be patient.")
  (pdj:venv-mkvirtualenv toxic:py-exec toxic:test-venv-name)
  (let ((pdj:py-requirements-file "requirements.txt")
	(pdj:py-bootstrap-buffer-name (concat "*" toxic:bootstrap-buffer-name "*"))
	(pdj:py-pip-command "pip"))
    (pdj:py-install-requirements-blocking))
  (venv-workon toxic:original-venv-name))

(defun toxic:--link-stuff ()
  "Creates symlinks to the toxicbuild scripts and lib so
   we can use the dev version in our test instance"

  (setq toxic:--ln-toxicslave
    (format "ln -s %sscripts/toxicslave %stoxicslave"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicmaster
    (format "ln -s %sscripts/toxicmaster %stoxicmaster"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicpoller
    (format "ln -s %sscripts/toxicpoller %stoxicpoller"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicsecrets
    (format "ln -s %sscripts/toxicsecrets %stoxicsecrets"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicintegrations
    (format "ln -s %sscripts/toxicintegrations %stoxicintegrations"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicoutput
    (format "ln -s %sscripts/toxicoutput %stoxicoutput"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicweb
    (format "ln -s %sscripts/toxicweb %stoxicweb"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicbuild-script
    (format "ln -s %sscripts/toxicbuild %stoxicbuild-script"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--ln-toxicbuild
    (format "ln -s %stoxicbuild %stoxicbuild"
	    toxic:--project-dir toxic:test-env-dir))

  (setq toxic:--link-everything
    (concat toxic:--ln-toxicslave " && " toxic:--ln-toxicmaster " && "
	    toxic:--ln-toxicbuild-script " && " toxic:--ln-toxicbuild
	    " && " toxic:--ln-toxicweb " && " toxic:--ln-toxicintegrations
	    " && " toxic:--ln-toxicoutput " && " toxic:--ln-toxicpoller
	    " && " toxic:--ln-toxicsecrets))

  (pdj:shell-command-on-project-directory toxic:--link-everything
					  (concat "*" "no-output" "*")))


(defun toxic:create-test-env ()
  "Creates a new test environment"

  (interactive)

  (defvar toxic:--create-cmd (concat toxic:create-test-env-command
				     toxic:test-env-path))

  (unless (file-exists-p toxic:test-env-dir)
    (make-directory toxic:test-env-dir))

  (setq toxic:--project-dir pdj:project-directory)

  (switch-to-buffer (get-buffer-create (concat "*" toxic:bootstrap-buffer-name "*")))
  (pdj:print "Hi, there!\n")
  (pdj:print " I'm gonna create a new toxicbuild installation for dev purposes.\n\n")
  (if (file-exists-p toxic:test-env-path)
      (message "toxic-env-path exists. Skipping it.")
    (progn
      (deferred:$
	(deferred:next
	  (lambda ()
	    (toxic:--link-stuff)))

	(deferred:nextc it
	  (lambda ()
	    (toxic:--create-venv)))

	(deferred:nextc it
	  (lambda ()
	    (goto-char (point-max))
	    (pdj:print "\n\n\nNow let's create a new dev instance.\n\n")
	    (let ((pdj:project-directory toxic:--project-dir))
	      (defvar old-path (getenv "PYTHONPATH"))
	      (setenv "PYTHONPATH" pdj:project-directory)
	      (pdj:run-in-term-on-project-directory toxic:--create-cmd
						    toxic:bootstrap-buffer-name)
	      (setenv "PYTHONPATH" old-path))))))))

(defun toxic:--run-in-env-on-test-dir (toxic-cmd buffer-name)

  (let ((default-directory toxic:test-env-dir))
    (venv-workon toxic:test-venv-name)
    (defvar old-path (getenv "PYTHONPATH"))
    (setenv "PYTHONPATH" toxic:test-env-dir)
    (let ((pdj:multi-term-switch-to-buffer nil))
      (pdj:run-in-term toxic-cmd buffer-name))
    (setenv "PYTHONPATH" old-path)
    (venv-workon toxic:original-venv-name)))

(defun toxic:--kill-buffer-shell-process (process-buffer-name)

  (defvar toxic:--process2kill nil)
  (defvar toxic:--buffer-name nil)

  (setq toxic:--buffer-name (concat "*" process-buffer-name "*"))
  (setq toxic:--process2kill (get-buffer-process toxic:--buffer-name))
  (kill-process toxic:--process2kill))


(defun toxic:--buffer-has-process (process-buffer-name)

  (defvar toxic:--buffer-name nil)

  (setq toxic:--buffer-name (concat "*" process-buffer-name "*"))
  (get-buffer-process toxic:--buffer-name))


(defun toxic:start-slave ()
  "Starts a slave instance in the test env"

  (interactive)

  (defvar toxic:--slave-path nil)
  (setq toxic:--slave-path (concat toxic:test-env-path "slave/"))
  (defvar toxic:--start-slave-cmd
    (format "%s %stoxicslave start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--slave-path toxic:loglevel))

  (toxic:--run-in-env-on-test-dir
   toxic:--start-slave-cmd toxic:slave-buffer-name))


(defun toxic:stop-slave ()
  "Stops the slave test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:slave-buffer-name))


(defun toxic:restart-slave ()
  "Restarts the slave test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-slave)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-slave)))))


(defun toxic:start-master ()
  "Starts a master instance in the test env"

  (interactive)

  (defvar toxic:--master-path nil)
  (setq toxic:--master-path (concat toxic:test-env-path "master/"))
  (defvar toxic:--start-master-cmd
    (format "%s %stoxicmaster start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--master-path toxic:loglevel))

  (defvar toxic:--master-buffer-name "toxicmaster")

  (toxic:--run-in-env-on-test-dir
   toxic:--start-master-cmd toxic:--master-buffer-name))


(defun toxic:stop-master ()
  "Stops the master test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:--master-buffer-name))


(defun toxic:restart-master ()
  "Restarts the master test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-master)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-master)))))


(defun toxic:start-output ()
  "Starts a toxicbuild output instance in the test env"

  (interactive)

  (defvar toxic:--output-path nil)
  (setq toxic:--output-path (concat toxic:test-env-path "output/"))
  (defvar toxic:--start-output-cmd
    (format "%s %stoxicoutput start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--output-path toxic:loglevel))

  (defvar toxic:--output-buffer-name "toxicoutput")

  (toxic:--run-in-env-on-test-dir
   toxic:--start-output-cmd toxic:--output-buffer-name))


(defun toxic:stop-output ()
  "Stops the toxicoutput test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:--output-buffer-name))


(defun toxic:restart-output ()
  "Restarts the toxicoutput test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-output)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-output)))))


(defun toxic:start-integrations ()
  "Starts a toxicbuild integrations instance in the test env"

  (interactive)

  (defvar toxic:--integrations-path nil)
  (setq toxic:--integrations-path (concat toxic:test-env-path "integrations/"))
  (defvar toxic:--start-integrations-cmd
    (format "%s %stoxicintegrations start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--integrations-path toxic:loglevel))

  (defvar toxic:--integrations-buffer-name "toxicintegrations")

  (toxic:--run-in-env-on-test-dir
   toxic:--start-integrations-cmd toxic:--integrations-buffer-name))


(defun toxic:stop-integrations ()
  "Stops the toxicbuild integrations test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:--integrations-buffer-name))


(defun toxic:restart-integrations ()
  "Restarts the integrations test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-integrations)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-integrations)))))


(defun toxic:start-poller ()
  "Starts a master's poller instance in the test env"

  (interactive)

  (defvar toxic:--poller-path nil)
  (setq toxic:--poller-path (concat toxic:test-env-path "poller/"))
  (defvar toxic:--start-poller-cmd
    (format "%s %stoxicpoller start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--poller-path toxic:loglevel))

  (defvar toxic:--poller-buffer-name "toxicpoller")

  (toxic:--run-in-env-on-test-dir
   toxic:--start-poller-cmd toxic:--poller-buffer-name))


(defun toxic:stop-poller ()
  "Stops the poller test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:--poller-buffer-name))


(defun toxic:restart-poller ()
  "Restarts the master' poller test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-poller)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-poller)))))

(defun toxic:start-secrets ()
  "Starts a master's secrets instance in the test env"

  (interactive)

  (defvar toxic:--secrets-path nil)
  (setq toxic:--secrets-path (concat toxic:test-env-path "secrets/"))
  (defvar toxic:--start-secrets-cmd
    (format "%s %stoxicsecrets start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--secrets-path toxic:loglevel))

  (defvar toxic:--secrets-buffer-name "toxicsecrets")

  (toxic:--run-in-env-on-test-dir
   toxic:--start-secrets-cmd toxic:--secrets-buffer-name))


(defun toxic:stop-secrets ()
  "Stops the secrets test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:--secrets-buffer-name))


(defun toxic:restart-secrets ()
  "Restarts the master' secrets test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-secrets)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-secrets)))))


(defun toxic:start-webui ()
  "Starts a web ui instance in the test env"

  (interactive)

  (defvar toxic:--webui-path nil)
  (setq toxic:--webui-path (concat toxic:test-env-path "ui/"))
  (defvar toxic:--start-webui-cmd
    (format "%s %stoxicweb start %s --loglevel=%s"
	    toxic:py-venv-exec toxic:test-env-dir toxic:--webui-path toxic:loglevel))

  (defvar toxic:--webui-buffer-name "webui")
  (toxic:--run-in-env-on-test-dir
   toxic:--start-webui-cmd toxic:webui-buffer-name))


(defun toxic:stop-webui ()
  "Stops the master test instance"

  (interactive)

  (toxic:--kill-buffer-shell-process toxic:webui-buffer-name))


(defun toxic:restart-webui ()
  "Restarts the webui test instance"

  (interactive)

  (deferred:$
    (deferred:next
      (lambda ()
	(toxic:stop-webui)))

    (deferred:nextc it
      (lambda ()
	(toxic:start-webui)))))


(defun toxic:start-all ()
  "Starts everything"

  (interactive)

  (toxic:start-slave)
  (toxic:start-poller)
  (toxic:start-secrets)
  (toxic:start-master)
  (toxic:start-integrations)
  (toxic:start-output)
  (toxic:start-webui))


(defun toxic:stop-all ()
  "Stops everything"

  (interactive)

  (toxic:stop-slave)
  (toxic:stop-poller)
  (toxic:stop-secrets)
  (toxic:stop-master)
  (toxic:stop-integrations)
  (toxic:stop-output)
  (toxic:stop-webui))


(defun toxic:restart-all ()
  "Restarts everything"

  (interactive)

  (toxic:restart-slave)
  (toxic:restart-master)
  (toxic:restart-poller)
  (toxic:restart-secrets)
  (toxic:restart-integrations)
  (toxic:restart-output)
  (toxic:restart-webui))


(defun toxic:fs-watcher (event)
  "Triggered by changes in toxicbuild files. Restarts servers."

  (defvar toxic:--event-file nil)
  (defvar toxic:--event-type nil)

  (setq toxic:--event-file (nth 2 event))
  (setq toxic:--event-type (nth 1 event))

  (if (eq toxic:--event-type 'changed)
      (if (string-match-p (regexp-quote "toxicbuild/master")
			  toxic:--event-file)
	  (toxic:restart-master)
	(if (string-match-p (regexp-quote "toxicbuild/poller")
			  toxic:--event-file)
	    (toxic:restart-poller)
	  (if (string-match-p (regexp-quote "toxicbuild/slave")
			      toxic:--event-file)
	      (toxic:restart-slave)
	    (if (string-match-p (regexp-quote "toxicbuild/ui")
				toxic:--event-file)
		(toxic:restart-webui)
	      (if (string-match-p (regexp-quote "toxicbuild/integrations")
				  toxic:--event-file)
		  (toxic:restart-integrations)
		(if (string-match-p (regexp-quote "toxicbuild/output")
				    toxic:--event-file)
		    (toxic:restart-output)
		  (if (string-match-p (regexp-quote "toxicbuild/secrets")
				    toxic:--event-file)
		    (toxic:restart-secrets))))))))))


(defun toxic:add-watcher ()

  (hack-local-variables)

  (defvar toxic:--master-path nil)
  (setq toxic:--master-path (concat pdj:project-directory
				    "toxicbuild/master"))

  (defvar toxic:--slave-path nil)
  (setq toxic:--slave-path (concat pdj:project-directory
				   "toxicbuild/slave"))

  (defvar toxic:--integrations-path nil)
  (setq toxic:--integrations-path (concat pdj:project-directory
					  "toxicbuild/integrations"))

  (defvar toxic:--output-path nil)
  (setq toxic:--output-path (concat pdj:project-directory
				    "toxicbuild/output"))

  (defvar toxic:--ui-path nil)
  (setq toxic:--ui-path (concat pdj:project-directory
				    "toxicbuild/ui"))

  (file-notify-add-watch toxic:--master-path '(change change)
			 'toxic:fs-watcher)

  (file-notify-add-watch toxic:--slave-path '(change change)
			 'toxic:fs-watcher)

  (file-notify-add-watch toxic:--integrations-path '(change change)
			 'toxic:fs-watcher)

  (file-notify-add-watch toxic:--output-path '(change change)
			 'toxic:fs-watcher)

  (file-notify-add-watch toxic:--ui-path '(change change)
			 'toxic:fs-watcher))


;; menu
(defun toxic:create-menu ()

  (interactive)

  (define-key-after global-map [menu-bar toxic-menu]
    (cons "ToxicDev" (make-sparse-keymap "ToxicDev")) 'Project)

  ;; Emacs menus are stupid. The order the items appear in the menu
  ;; is the oposite that they are declared here
  (define-key global-map [menu-bar toxic-menu toxic-restart-all]
    '(menu-item "Restart all" toxic:restart-all
		:visible (progn (and (toxic:--buffer-has-process
				      toxic:webui-buffer-name)
				     (toxic:--buffer-has-process
				      toxic:master-buffer-name)
				     (toxic:--buffer-has-process
				      toxic:slave-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-all]
    '(menu-item "Stop all" toxic:stop-all
		:visible (progn (and (toxic:--buffer-has-process
				      toxic:webui-buffer-name)
				     (toxic:--buffer-has-process
				      toxic:master-buffer-name)
				     (toxic:--buffer-has-process
				      toxic:slave-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-start-all]
    '(menu-item "Start all" toxic:start-all
		:visible (progn (and (not (toxic:--buffer-has-process
				      toxic:webui-buffer-name))
				(not (toxic:--buffer-has-process
				      toxic:master-buffer-name))
				(not (toxic:--buffer-has-process
				      toxic:slave-buffer-name))))))

  (define-key global-map [menu-bar toxic-menu toxic-fourth-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-restart-webui]
    '(menu-item "Restart toxicweb" toxic:restart-webui
		:visible (progn (toxic:--buffer-has-process
				 toxic:webui-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-webui]
    '(menu-item "Stop toxicweb" toxic:stop-webui
		:visible (progn (toxic:--buffer-has-process
				 toxic:webui-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-webui]
    '(menu-item "Start toxicweb" toxic:start-webui
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:webui-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-integrations-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-restart-integrations]
    '(menu-item "Restart integrations" toxic:restart-integrations
		:visible (progn (toxic:--buffer-has-process
				 toxic:integrations-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-integrations]
    '(menu-item "Stop integrations" toxic:stop-integrations
		:visible (progn (toxic:--buffer-has-process
				 toxic:integrations-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-integrations]
    '(menu-item "Start integrations" toxic:start-integrations
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:integrations-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-output-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-restart-output]
    '(menu-item "Restart output" toxic:restart-output
		:visible (progn (toxic:--buffer-has-process
				 toxic:output-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-output]
    '(menu-item "Stop output" toxic:stop-output
		:visible (progn (toxic:--buffer-has-process
				 toxic:output-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-output]
    '(menu-item "Start output" toxic:start-output
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:output-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-third-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-restart-master]
    '(menu-item "Restart toxicmaster" toxic:restart-master
		:visible (progn (toxic:--buffer-has-process
				 toxic:master-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-master]
    '(menu-item "Stop toxicmaster" toxic:stop-master
		:visible (progn (toxic:--buffer-has-process
				 toxic:master-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-master]
    '(menu-item "Start toxicmaster" toxic:start-master
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:master-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-second-minus-minus-separator]
    '(menu-item "--"))


  (define-key global-map [menu-bar toxic-menu toxic-restart-poller]
    '(menu-item "Restart toxicpoller" toxic:restart-poller
		:visible (progn (toxic:--buffer-has-process
				 toxic:poller-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-poller]
    '(menu-item "Stop toxicpoller" toxic:stop-poller
		:visible (progn (toxic:--buffer-has-process
				 toxic:poller-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-poller]
    '(menu-item "Start toxicpoller" toxic:start-poller
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:poller-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-restart-secrets]
    '(menu-item "Restart toxicsecrets" toxic:restart-secrets
		:visible (progn (toxic:--buffer-has-process
				 toxic:secrets-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-secrets]
    '(menu-item "Stop toxicsecrets" toxic:stop-secrets
		:visible (progn (toxic:--buffer-has-process
				 toxic:secrets-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-secrets]
    '(menu-item "Start toxicsecrets" toxic:start-secrets
		:visible (progn (not (toxic:--buffer-has-process
				      toxic:secrets-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-second-other-minus-minus-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-restart-slave]
    '(menu-item "Restart toxicslave" toxic:restart-slave
		:visible (progn (toxic:--buffer-has-process
				toxic:slave-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-stop-slave]
    '(menu-item "Stop toxicslave" toxic:stop-slave
		:visible (progn (toxic:--buffer-has-process
				toxic:slave-buffer-name))))

  (define-key global-map [menu-bar toxic-menu toxic-start-slave]
    '(menu-item "Start toxicslave" toxic:start-slave
		:visible (progn (not (toxic:--buffer-has-process
				     toxic:slave-buffer-name)))))

  (define-key global-map [menu-bar toxic-menu toxic-first-separator]
    '(menu-item "--"))

  (define-key global-map [menu-bar toxic-menu toxic-create-testenv]
    '(menu-item "Create test environment" toxic:create-test-env)))


(defun toxic:setup ()

  (toxic:create-menu)
  (toxic:custom-keyboard-hooks)
  (toxic:add-watcher))


(add-hook 'python-mode-hook 'toxic:setup)
