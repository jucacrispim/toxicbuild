Feature:
    A user inserts and deletes a repo in web ui, enabling and disabling
    notifications.

    Scenario:
        The user navigates to the add repo page

        Given the user is logged in the web interface
        When he clicks in the add repository link
        Then he sees the add repository page

    Scenario:
        The user adds a new repository

        Given the user is in the add repo page
        When he fills the name with a repo name
        And fills the url field with a repo url
        And clicks in the add button
        Then he sees the "Repository added" message

    Scenario:
        The user toggles the advanced configuration

        Given the user is in the repository settings page
        When he clicks in the Advanced element
        Then he sees the advanced options
        And sees the advanced help in the side bar

    Scenario:
        The user updates the parallel builds configuration

        Given the user is in the repository settings page
        And he sees the advanced options
        When he fills the parallel builds with 2
        And clicks in the save button
        Then he sees the "Repository updated" message

    Scenario:
        The user adds a branch configuration to the repository

        Given the user is in the repository settings page
        And he sees the advanced options
        When he clicks in the add branch button
        And fills the branch name
        And clicks in the add branch button
        Then he sees the new branch config in the list

    Scenario:
        The user removes a branch configuration

        Given the user already added a branch config
        When he clicks in the remove branch config button
        Then he sees the no branch config info in the list

    Scenario:
        The user disables a slave

        Given the user is in the repository settings page
        When he clicks in the slave enabled check button
        Then he sees the slave disabled check button

    Scenario:
        The user enables a slave

        Given the user is in the repository settings page
        When he clicks in the slave disabled check button
        Then he sees the slave enabled check button

    Scenario:
        The user disables a repository

        Given the user is in the repository settings page
        When he clicks in the repo enabled check button
        Then he sees the repo disabled check button

    Scenario:
        The user navigates to the repository management page

        Given the user is in the repository settings page
        When he clicks in the close button
        And clicks in the manage repositories link
        Then he sees a list of repositories

    Scenario:
        The user enables a repository

        Given the user is in the repository management page
        When he clicks in the repo disabled ckeck button
        Then he sees the repo enabled check button

    Scenario:
        The user navigates to the repository settings page

        Given the user is in the repository management page
        When he clicks in the toxicbuild logo
        And clicks in the repo menu
        And clicks in the repo settings link
        Then he sees the repository settings page

    Scenario:
        The user deletes a repository

        Given the user is in the repository settings page
        When he clicks in the Advanced element
        And clicks in the delete repo button
        And clicks in the delete repo button in the modal
        Then he sees the "Repository removed" message
