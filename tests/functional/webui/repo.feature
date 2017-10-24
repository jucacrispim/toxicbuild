Feature:
    A user inserts and deletes a repo in web ui, enabling and disabling
    output methods plugins.

    Scenario:
        The user inserts a new repo without required information

        Given the user is logged in the web interface
        When he clicks in the add repo button
        And sees the repo modal
        And fills the repo name field with "toxictest"
        And clicks in the save repo button
        Then he sees the required fields in red

    Scenario:
        The user inserts a new repo and that works

        Given the user already tried to save a repo
        When he fills the url field with a repo url
        And selects a slave named "repo-slave"
        And clicks in the save repo button
        Then he sees the "Repository is being created. Please wait." message
        And the repo status "pending"
        And the repo status "success"

    Scenario:
        The user enables an output method plugin

        Given the user already inserted a new repo
        When he clicks in the configure output methods button
        And sees the output methods modal
        And clicks in the enable ckeckbox
        And fills the webhook url field with "https://something.net/bla"
        And fills the channel name field with "my-channel"
        And fills the branches field with "master, dev, release"
        And fills the statuses field with "fail, exeption, warning, success"
        And clicks in the save plugin button
        Then he sees the "Plugin slack-notification enabled" message

    Scenario:
        A user removes a repo

        Given the user is logged in the web interface and has a repo
        When he clicks in the edit repo button
        And sees the repo modal
        And clicks in the delete repo button
        Then he sees the "Repository removed." message
        And the repo is removed from the repo list
