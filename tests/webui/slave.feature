Feature: A user inserts and removes a slave in the web interface

    Scenario: The user navigates to the add slave page

        Given the user is logged in the web interface
        When he clicks in the settings button
        And clicks in the Manage slaves menu
        And clicks in the add slave button
        Then he sees the add slave page

    Scenario: The user inserts a new slave

        Given the user is in the add slave page
        When he fills the slave name field
        And fills the host field
        And fills the port field
        And fills the token field
        And clicks in the add new slave button
        Then he sees the "Slave added" message

    Scenario: The user updates slave ssl information

        Given the user is in the slave settings page
        When he clicks in the use ssl button
        And clicks in the save changes button
        Then he sees the "Slave updated" message

    Scenario: The user lists all the slaves

        Given the user is in the slave settings page
        When he clicks in the close page button
        Then he sees the slaves list

    Scenario: An user removes a slave

        Given the user is in the slaves list page
        When he navigates to the slave settings page
        And clicks in the delete slave button
        And clicks in the delete slave button in the modal
        Then he sees the "Slave removed" message
