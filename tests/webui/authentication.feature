Feature: The web user interface can authenticate users

    Scenario: Someone try to access a page without being logged.
        When someone tries to access a waterfall url without being logged
        Then he sees the login page

    Scenario: Tries to login without required information
        Given the user is in the login page
        When he inserts "someguy" as user name
        And clicks in the login button
        Then he sees the red warning in the password field

    Scenario: Tries to login with invalid credentials
        Given the user is in the login page
        When he inserts "someguy" as user name
        And inserts "a123" as password
        And clicks in the login button
        Then he sees the invalid credentials message

    Scenario: Do login
        Given the user is in the login page
        When he inserts "someguy" as user name
        And inserts "123" as password
        And clicks in the login button
        Then he sees the main page

    Scenario: Do logout
        Given the user is logged in the web interface
        When he clicks in the logout link
        Then he sees the login page
