Feature:
    A user inserts and deletes a repo in web ui

    Scenario: The user inserts a new repo without required information
        Given the user is logged in the web interface
        When he clicks in the add repo button
        And sees the repo modal
        And fills the repo name field with "toxictest"
        And clicks in the save repo button
        Then he sees the required fields in red

    Scenario: The user inserts a new repo and that works
        Given the user already tried to save a repo
        When he fills the url field with a repo url
        And fills the update seconds field with "1"
        And selects a slave named "repo-slave"
        And clicks in the save repo button
        Then he sees the "Repository is being created. Please wait." message
        And the repo status "pending"
        And the repo status "success"

    Scenario: A user removes a repo
        Given the user is logged in the web interface and has a repo
        When he clicks in the edit repo button
        And sees the repo modal
        And clicks in the delete repo button
        Then he sees the "Repository removed." message
        And the repo is removed from the repo list
