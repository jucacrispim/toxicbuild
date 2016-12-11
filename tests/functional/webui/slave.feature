Feature: A user inserts and removes a slave in the web interface

    Scenario: The user inserts a new slave without required information
        Given the user is logged in the web interface
	When he clicks in the add slave button
	And sees the slave modal
	And fills the name field with "some-slave"
	And fills the host field with "localhost"
	And fills the port field with "7777"
	And clicks in the save button
	Then he sees the token field label in red

    Scenario: The user inserts a new slave and that works
        Given the user already tried to save a slave
	When fills the token field with "slave-secret-token"
        And clicks in the save button
	Then he sees the new slave in the slave list

    Scenario: A user removes a slave
        Given a user is logged in the system and has a slave
	When he clicks in the edit slave button
        And sees the slave modal
	And clicks in the delete button
	Then the slave is removed from the slave list
