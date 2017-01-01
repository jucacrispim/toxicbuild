(require 'pdj-feature)


(defun toxic:behave-with-selenium ()
  "Starts a Xvfb server before the tests and kill it after."

  (interactive)

  (defvar toxic--xvfb-start-command "Xvfb :99  -ac -screen 0, 1368x768x24 &")
  (defvar toxic--xvfb-stop-command "killall Xvfb")
  (setq old-display (getenv "DISPLAY"))
  (setenv "DISPLAY" ":99")
  (shell-command toxic--xvfb-start-command)

  ;; sentinel to the tests process. When it finished we
  ;; must to kill the Xvfb process
  (defun pdj:--kill-xvfb (process event)
    (if (equal event "finished\n")
	(progn
	  (let ((kill-buffer-query-functions
		(delq 'process-kill-buffer-query-function
		      kill-buffer-query-functions)))
	    (kill-buffer "*Async Shell Command*")
	    (message old-display)
	    (setenv "DISPLAY" old-display)
	    (shell-command toxic--xvfb-stop-command)))))

  (let ((multi-term-close-on-finish t))
    (pdj:feature-run-test-file)
    (set-process-sentinel (get-process pdj:behave-buffer-name)
			  'pdj:--kill-xvfb)))


(defun toxic:feature-hooks ()

    (local-set-key (kbd "C-c n") 'toxic:behave-with-selenium))

(add-hook 'pdj:feature-mode-hook 'toxic:feature-hooks)
